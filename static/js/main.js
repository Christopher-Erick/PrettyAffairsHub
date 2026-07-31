(() => {
  const header = document.querySelector("[data-header]");
  const toggle = document.querySelector("[data-nav-toggle]");
  const mobileNav = document.querySelector("[data-mobile-nav]");
  const themeToggle = document.querySelector("[data-theme-toggle]");
  const themeColorMeta = document.querySelector('meta[name="theme-color"]');

  const applyTheme = (theme) => {
    const next = theme === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    try {
      if (next === "dark") {
        localStorage.setItem("pah-theme", "dark");
      } else {
        localStorage.removeItem("pah-theme");
      }
    } catch (e) {
      /* ignore private mode */
    }
    if (themeToggle) {
      themeToggle.setAttribute(
        "aria-label",
        next === "dark" ? "Switch to light mode" : "Switch to dark mode"
      );
    }
    if (themeColorMeta) {
      const light = themeColorMeta.getAttribute("data-theme-color-light") || "#1c1715";
      const dark = themeColorMeta.getAttribute("data-theme-color-dark") || "#14100f";
      themeColorMeta.setAttribute("content", next === "dark" ? dark : light);
    }
  };

  const currentTheme = () =>
    document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";

  applyTheme(currentTheme());

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      applyTheme(currentTheme() === "dark" ? "light" : "dark");
    });
  }

  if (header) {
    const onScroll = () => {
      header.classList.toggle("is-scrolled", window.scrollY > 8);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  if (toggle && mobileNav) {
    toggle.addEventListener("click", () => {
      const open = mobileNav.hasAttribute("hidden");
      if (open) {
        mobileNav.removeAttribute("hidden");
      } else {
        mobileNav.setAttribute("hidden", "");
      }
      toggle.setAttribute("aria-expanded", String(open));
    });

    window.addEventListener("resize", () => {
      if (window.matchMedia("(min-width: 900px)").matches && !mobileNav.hasAttribute("hidden")) {
        mobileNav.setAttribute("hidden", "");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  const shopSearch = document.querySelector("[data-shop-search]");
  if (shopSearch) {
    const input = shopSearch.querySelector("[data-shop-search-input]");
    const clear = shopSearch.querySelector("[data-shop-search-clear]");
    const quickTerms = shopSearch.querySelectorAll("[data-search-term]");

    const syncClear = () => {
      if (clear && input) clear.hidden = !input.value;
    };

    if (input) {
      input.addEventListener("input", syncClear);
      syncClear();
    }

    if (clear && input) {
      clear.addEventListener("click", () => {
        input.value = "";
        syncClear();
        window.location.assign(shopSearch.dataset.clearUrl || window.location.pathname);
      });
    }

    quickTerms.forEach((button) => {
      button.addEventListener("click", () => {
        if (!input) return;
        input.value = button.dataset.searchTerm || "";
        syncClear();
        shopSearch.requestSubmit();
      });
    });
  }

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduceMotion && "IntersectionObserver" in window) {
    document
      .querySelectorAll(".section, .band, .story-grid, .product-card")
      .forEach((el) => el.classList.add("reveal-on-scroll"));

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -6% 0px" }
    );

    document.querySelectorAll(".reveal-on-scroll").forEach((el) => observer.observe(el));
  }
})();
