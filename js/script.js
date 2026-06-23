const content = document.getElementById("content");

const pageTitles = {
  home: "CypherDocs | Cypher-Monarch",
  cyphergate: "CypherGate | CypherDocs",
  spectra: "Spectra | CypherDocs",
  chronolog: "ChronoLOG | CypherDocs",
  monarchdots: "MonarchDots | CypherDocs",
};

function initializeInstallTabs() {
  const tabs = document.querySelectorAll(".install-tab");
  const panels = document.querySelectorAll(".install-panel");

  if (!tabs.length || !panels.length) return;

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.target;

      tabs.forEach((t) => t.classList.remove("active"));
      panels.forEach((panel) => panel.classList.remove("active"));

      tab.classList.add("active");

      const targetPanel = document.getElementById(target);
      if (targetPanel) {
        targetPanel.classList.add("active");
      }
    });
  });
}

function initializePage() {
  lucide.createIcons();
  initializeInstallTabs();
}

async function loadPage(page) {
  try {
    const response = await fetch(`projects/${page}.html`);

    if (!response.ok) {
      throw new Error("Page not found");
    }

    const html = await response.text();
    content.innerHTML = html;

    document.title =
      pageTitles[page] || "CypherDocs | Cypher-Monarch";

    initializePage();
  } catch {
    content.innerHTML = `
      <section>
        <h1>404</h1>
        <p>Page not found.</p>
      </section>
    `;

    document.title = "404 | CypherDocs";
  }
}

function handleRoute() {
  const page = location.hash.replace("#", "") || "home";
  loadPage(page);
}

window.addEventListener("hashchange", handleRoute);
handleRoute();