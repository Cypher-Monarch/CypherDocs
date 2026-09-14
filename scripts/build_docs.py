#!/usr/bin/env python3

from __future__ import annotations

import html
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PROJECT_NAME = "CypherGate"
PROJECT_REPO = "CypherGate"

PAGES = {
    "architecture": "Architecture",
    "assumptions": "Assumptions",
    "codebase": "Codebase",
    "ipc": "IPC",
    "security-model": "Security Model",
    "settings": "Settings",
    "theming": "Theming",
}

MARKDOWN_EXTENSIONS = [
    "fenced_code",
    "tables",
    "sane_lists",
]


def slugify(value: str) -> str:
    """Turn a heading into a stable, URL-safe fragment ID."""
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    value = re.sub(r"[\s_-]+", "-", value)
    return value.strip("-") or "section"


def load_template(template_path: Path) -> str:
    return template_path.read_text(encoding="utf-8")


def render_template(template: str, values: dict[str, str]) -> str:
    rendered = template

    for key, value in values.items():
        rendered = rendered.replace("{{ " + key + " }}", value)

    return rendered


def git_date(source_file: Path) -> str:
    """
    Return the last commit date for a source file.

    The docs repository is checked out as the current working tree, so the
    file path is resolved relative to the repository root.
    """
    try:
        repo_root = Path(
            subprocess.check_output(
                ["git", "-C", str(source_file.parent), "rev-parse", "--show-toplevel"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        )

        relative_file = source_file.relative_to(repo_root)

        value = subprocess.check_output(
            [
                "git",
                "-C",
                str(repo_root),
                "log",
                "-1",
                "--format=%cI",
                "--",
                str(relative_file),
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        if value:
            return value[:10]
    except (OSError, subprocess.CalledProcessError, ValueError):
        pass

    return datetime.now(timezone.utc).date().isoformat()


def format_date(iso_date: str) -> str:
    try:
        return datetime.fromisoformat(iso_date).strftime("%B %-d, %Y")
    except ValueError:
        return iso_date


def extract_headings(source: str) -> list[tuple[int, str, str]]:
    """
    Extract ATX Markdown headings and assign deterministic, unique IDs.

    Returns:
        (level, visible_title, fragment_id)
    """
    headings = []
    used_ids: dict[str, int] = {}

    for line in source.splitlines():
        match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue

        level = len(match.group(1))
        title = match.group(2).strip()

        # Avoid treating headings inside fenced code blocks as real headings.
        headings.append((level, title, ""))

    # Re-run with fenced-code awareness.
    headings = []
    used_ids = {}
    in_fence = False

    for line in source.splitlines():
        if re.match(r"^\s{0,3}(```|~~~)", line):
            in_fence = not in_fence
            continue

        if in_fence:
            continue

        match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue

        level = len(match.group(1))
        title = match.group(2).strip()
        base_id = slugify(title)

        count = used_ids.get(base_id, 0)
        used_ids[base_id] = count + 1
        fragment_id = base_id if count == 0 else f"{base_id}-{count + 1}"

        headings.append((level, title, fragment_id))

    return headings


def inject_heading_ids(rendered_html: str, headings: list[tuple[int, str, str]]) -> str:
    """
    Add the IDs generated from the Markdown source to rendered h1-h6 elements.

    Python-Markdown can generate IDs itself, but doing it here keeps the
    source-heading slug rules and TOC fragments under our control.
    """
    heading_index = 0

    pattern = re.compile(
        r"<h([1-6])(?:\s[^>]*)?>(.*?)</h\1>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        nonlocal heading_index

        if heading_index >= len(headings):
            return match.group(0)

        level, _, fragment_id = headings[heading_index]
        heading_index += 1

        if int(match.group(1)) != level:
            return match.group(0)

        inner = match.group(2)
        inner = re.sub(r'\s+id="[^"]*"', "", inner)

        return (
            f'<h{level} id="{html.escape(fragment_id, quote=True)}">{inner}</h{level}>'
        )

    return pattern.sub(replace, rendered_html)


def render_markdown(source: str) -> tuple[str, list[tuple[int, str, str]]]:
    try:
        import markdown
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: markdown. Install it with: pip install markdown"
        ) from exc

    headings = extract_headings(source)

    markdown_parser = markdown.Markdown(
        extensions=MARKDOWN_EXTENSIONS,
        output_format="html5",
    )

    rendered = markdown_parser.convert(source)
    rendered = inject_heading_ids(rendered, headings)

    return rendered, headings


def build_toc(headings: list[tuple[int, str, str]]) -> str:
    """
    Build the compact right-hand TOC.

    The document's h1 is treated as the page title and omitted from the TOC.
    h2-h6 entries are retained.
    """
    items = []

    for level, title, fragment_id in headings:
        if level == 1:
            continue

        # Escape the visible title because it originates in Markdown source.
        label = html.escape(title)
        href = html.escape("#" + fragment_id, quote=True)

        items.append(f'<a href="{href}" class="toc-level-{level}">{label}</a>')

    if not items:
        return '<span class="docs-toc-empty">No sections</span>'

    return "\n".join(items)


def build_sidebar(active_slug: str | None, docs_root: str) -> str:
    """
    Build sidebar links relative to the current generated page.

    docs_root:
        Relative path from the generated page back to /cyphergate/docs/.
    """
    links = []

    overview_class = ' aria-current="page"' if active_slug is None else ""
    links.append(f'          <a href="{docs_root}"{overview_class}>Overview</a>')

    for slug, label in PAGES.items():
        active = ' aria-current="page"' if slug == active_slug else ""
        links.append(
            f'          <a href="{docs_root}{slug}/"{active}>{html.escape(label)}</a>'
        )

    return "\n".join(links)


def build_overview_content() -> str:
    """
    Keep the docs landing page intentionally small.

    The actual Markdown documents remain the source of truth for individual
    documentation pages.
    """
    updated = git_date(Path("docs"))
    updated_label = html.escape(format_date(updated))

    updated_html = (
        f'      <p class="docs-updated">Updated '
        f'<time datetime="{html.escape(updated)}">{updated_label}</time></p>'
    )

    return f"""      <p class="docs-eyebrow">CypherGate</p>

      <h1 id="documentation">CypherGate canonical documentation</h1>

      <p>The canonical documentation for CypherGate.</p>

{updated_html}"""


def page_values(
    *,
    title: str,
    description: str,
    stylesheet: str,
    script: str,
    docs_root: str,
    home: str,
    project: str,
    sidebar: str,
    toc: str,
    content: str,
) -> dict[str, str]:
    return {
        "title": title,
        "description": description,
        "stylesheet": stylesheet,
        "script": script,
        "docs_root": docs_root,
        "home": home,
        "project": project,
        "sidebar": sidebar,
        "toc": toc,
        "content": content,
    }


def build_overview(
    *,
    template: str,
    output_root: Path,
) -> None:
    docs_root = "./"
    stylesheet = "../../css/style.css"
    script = "../../js/script.js"
    home = "../../"
    project = "../"

    content = build_overview_content()

    toc = '<a href="#documentation">Documentation</a>'
    sidebar = build_sidebar(None, docs_root)

    rendered = render_template(
        template,
        page_values(
            title=f"{PROJECT_NAME} Documentation — CypherDocs",
            description=f"Canonical documentation for {PROJECT_NAME}.",
            stylesheet=stylesheet,
            script=script,
            docs_root="../",
            home=home,
            project=project,
            sidebar=sidebar,
            toc=toc,
            content=content,
        ),
    )

    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "index.html").write_text(rendered, encoding="utf-8")


def build_page(
    source_file: Path,
    *,
    template: str,
    output_root: Path,
) -> None:
    slug = source_file.stem
    title = PAGES.get(slug, slug.replace("-", " ").title())

    source = source_file.read_text(encoding="utf-8")
    content_html, headings = render_markdown(source)

    output_dir = output_root / slug
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generated pages live at /cyphergate/docs/<slug>/index.html.
    docs_root = "../"
    stylesheet = "../../../css/style.css"
    script = "../../../js/script.js"
    home = "../../../"
    project = "../../"

    sidebar = build_sidebar(slug, docs_root)
    toc = build_toc(headings)

    updated = git_date(source_file)
    updated_label = html.escape(format_date(updated))

    updated_html = (
        f'<p class="docs-updated">Updated '
        f'<time datetime="{html.escape(updated)}">{updated_label}</time></p>'
    )

    content_html = re.sub(
        r"(<h1[^>]*>.*?</h1>)",
        r"\1\n" + updated_html,
        content_html,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )

    content = (
        f'      <p class="docs-eyebrow">{html.escape(PROJECT_NAME)}</p>\n\n'
        f"{content_html}"
    )

    rendered = render_template(
        template,
        page_values(
            title=f"{title} — {PROJECT_NAME} — CypherDocs",
            description=f"{title} documentation for {PROJECT_NAME}.",
            stylesheet=stylesheet,
            script=script,
            docs_root="../../",
            home=home,
            project=project,
            sidebar=sidebar,
            toc=toc,
            content=content,
        ),
    )

    (output_dir / "index.html").write_text(rendered, encoding="utf-8")


def clean_generated_pages(output_root: Path) -> None:
    """
    Remove generated documentation directories for known source pages.

    Do not wipe the entire docs directory: the overview page and any future
    manually-managed assets should survive the build.
    """
    for slug in PAGES:
        target = output_root / slug
        if target.exists():
            shutil.rmtree(target)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Build CypherGate Markdown documentation into static HTML."
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Directory containing CypherGate docs/*.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("cyphergate/docs"),
        help="Generated documentation output directory.",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=Path("templates/docs.html"),
        help="HTML template path.",
    )

    args = parser.parse_args()

    source_root = args.source
    output_root = args.output
    template_path = args.template

    if not source_root.is_dir():
        raise SystemExit(f"Source directory does not exist: {source_root}")

    if not template_path.is_file():
        raise SystemExit(f"Template does not exist: {template_path}")

    template = load_template(template_path)

    output_root.mkdir(parents=True, exist_ok=True)
    clean_generated_pages(output_root)

    build_overview(
        template=template,
        output_root=output_root,
    )

    for slug in PAGES:
        source_file = source_root / f"{slug}.md"

        if not source_file.is_file():
            print(f"warning: missing source document: {source_file}")
            continue

        build_page(
            source_file,
            template=template,
            output_root=output_root,
        )

        print(f"built: {source_file} -> {output_root / slug / 'index.html'}")


if __name__ == "__main__":
    main()
