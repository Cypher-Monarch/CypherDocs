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

function initializeDocsNavigation() {
  const details = document.querySelectorAll(
    ".docs-sidebar details, .docs-toc details"
  );

  if (!details.length) return;

  const mediaQuery = window.matchMedia("(max-width: 768px)");

  const syncDetails = (event) => {
    details.forEach((element) => {
      element.open = !event.matches;
    });
  };

  syncDetails(mediaQuery);

  mediaQuery.addEventListener("change", syncDetails);
}

function initializeNavToggle() {
  const navToggle = document.getElementById("nav-toggle");
  const siteNav = document.getElementById("site-nav");

  if (!navToggle || !siteNav) return;

  navToggle.addEventListener("click", () => {
    siteNav.classList.toggle("open");

    const isExpanded = siteNav.classList.contains("open");
    navToggle.setAttribute("aria-expanded", isExpanded);
  });

  siteNav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      siteNav.classList.remove("open");
      navToggle.setAttribute("aria-expanded", "false");
    });
  });
}

function initializePage() {
  if (typeof lucide !== "undefined") {
    lucide.createIcons();
  }

  initializeInstallTabs();
  initializeDocsNavigation();
  initializeNavToggle();
}

initializePage();
