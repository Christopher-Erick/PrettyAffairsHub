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
    let navOpenScrollY = 0;

    const closeMobileNav = () => {
      if (mobileNav.hasAttribute("hidden")) return;
      mobileNav.setAttribute("hidden", "");
      toggle.setAttribute("aria-expanded", "false");
    };

    const openMobileNav = () => {
      mobileNav.removeAttribute("hidden");
      toggle.setAttribute("aria-expanded", "true");
      navOpenScrollY = window.scrollY;
    };

    toggle.addEventListener("click", () => {
      if (mobileNav.hasAttribute("hidden")) openMobileNav();
      else closeMobileNav();
    });

    // Close the menu once the page is scrolled (small screens).
    window.addEventListener(
      "scroll",
      () => {
        if (mobileNav.hasAttribute("hidden")) return;
        if (Math.abs(window.scrollY - navOpenScrollY) < 10) return;
        closeMobileNav();
      },
      { passive: true }
    );

    window.addEventListener("resize", () => {
      if (window.matchMedia("(min-width: 900px)").matches) closeMobileNav();
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

  const shopFilters = document.querySelector("[data-shop-filters]");
  if (shopFilters) {
    const desktopShop = window.matchMedia("(min-width: 900px)");
    const syncShopFilters = (event) => {
      shopFilters.open = event.matches;
    };
    syncShopFilters(desktopShop);
    desktopShop.addEventListener("change", syncShopFilters);
  }

  document.querySelectorAll("[data-fancy-select]").forEach((wrap) => {
    const select = wrap.querySelector("select");
    if (!select || wrap.dataset.enhanced === "true") return;

    const label = wrap.closest(".filter-control")?.querySelector(".field-label");
    const trigger = document.createElement("button");
    const valueEl = document.createElement("span");
    const menu = document.createElement("div");
    let optionButtons = [];

    wrap.dataset.enhanced = "true";
    wrap.classList.add("is-enhanced");
    select.tabIndex = -1;
    trigger.type = "button";
    trigger.className = "filter-select__trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    if (label) trigger.setAttribute("aria-labelledby", label.id || (label.id = `${select.id}-label`));
    valueEl.className = "filter-select__value";
    menu.className = "filter-select__menu";
    menu.setAttribute("role", "listbox");
    menu.hidden = true;

    const syncValue = () => {
      const selected = select.options[select.selectedIndex];
      valueEl.textContent = selected ? selected.textContent.trim() : "";
      optionButtons.forEach((button) => {
        const active = button.dataset.value === select.value;
        button.classList.toggle("is-selected", active);
        button.setAttribute("aria-selected", String(active));
      });
    };

    const closeMenu = () => {
      wrap.classList.remove("is-open");
      menu.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
    };

    const openMenu = () => {
      document.querySelectorAll("[data-fancy-select].is-open").forEach((other) => {
        if (other !== wrap) other.querySelector("[data-fancy-close]")?.click();
      });
      wrap.classList.add("is-open");
      menu.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      const selected = optionButtons.find((button) => button.classList.contains("is-selected"));
      (selected || optionButtons[0])?.focus();
    };

    const choose = (value) => {
      select.value = value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      syncValue();
      closeMenu();
      trigger.focus();
    };

    const buildMenu = () => {
      menu.innerHTML = "";
      optionButtons = [];
      [...select.children].forEach((node) => {
        if (node.tagName === "OPTGROUP") {
          const group = document.createElement("div");
          group.className = "filter-select__group";
          const groupLabel = document.createElement("span");
          groupLabel.className = "filter-select__group-label";
          groupLabel.textContent = node.label;
          group.appendChild(groupLabel);
          [...node.children].forEach((option) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "filter-select__option is-child";
            button.setAttribute("role", "option");
            button.dataset.value = option.value;
            button.textContent = option.textContent.trim();
            button.addEventListener("click", () => choose(option.value));
            group.appendChild(button);
            optionButtons.push(button);
          });
          menu.appendChild(group);
          return;
        }
        if (node.tagName !== "OPTION") return;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "filter-select__option";
        button.setAttribute("role", "option");
        button.dataset.value = node.value;
        button.textContent = node.textContent.trim();
        button.addEventListener("click", () => choose(node.value));
        menu.appendChild(button);
        optionButtons.push(button);
      });
    };

    const closeProxy = document.createElement("button");
    closeProxy.type = "button";
    closeProxy.hidden = true;
    closeProxy.setAttribute("data-fancy-close", "");
    closeProxy.addEventListener("click", closeMenu);

    trigger.appendChild(valueEl);
    wrap.appendChild(trigger);
    wrap.appendChild(menu);
    wrap.appendChild(closeProxy);
    buildMenu();
    syncValue();

    trigger.addEventListener("click", () => {
      if (wrap.classList.contains("is-open")) closeMenu();
      else openMenu();
    });

    trigger.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openMenu();
      }
    });

    menu.addEventListener("keydown", (event) => {
      const index = optionButtons.indexOf(document.activeElement);
      if (event.key === "Escape") {
        event.preventDefault();
        closeMenu();
        trigger.focus();
        return;
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        optionButtons[Math.min(index + 1, optionButtons.length - 1)]?.focus();
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        optionButtons[Math.max(index - 1, 0)]?.focus();
      }
      if (event.key === "Home") {
        event.preventDefault();
        optionButtons[0]?.focus();
      }
      if (event.key === "End") {
        event.preventDefault();
        optionButtons[optionButtons.length - 1]?.focus();
      }
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        document.activeElement?.click();
      }
    });

    document.addEventListener("click", (event) => {
      if (!wrap.contains(event.target)) closeMenu();
    });
  });

  document.querySelectorAll("[data-scroll-rail]").forEach((rail) => {
    const track = rail.querySelector("[data-scroll-track]");
    const previous = rail.querySelector("[data-scroll-prev]");
    const next = rail.querySelector("[data-scroll-next]");
    if (!track || !previous || !next) return;

    const syncArrows = () => {
      const maxScroll = track.scrollWidth - track.clientWidth;
      previous.disabled = track.scrollLeft <= 2;
      next.disabled = track.scrollLeft >= maxScroll - 2;
    };

    const move = (direction) => {
      track.scrollBy({
        left: direction * Math.max(track.clientWidth * 0.8, 240),
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      });
    };

    previous.addEventListener("click", () => move(-1));
    next.addEventListener("click", () => move(1));
    track.addEventListener("scroll", syncArrows, { passive: true });
    window.addEventListener("resize", syncArrows);
    syncArrows();
  });

  document.querySelectorAll("[data-product-card]").forEach((card) => {
    const image = card.querySelector("[data-card-image]");
    const variantInput = card.querySelector("[data-card-variant]");
    const shadeName = card.querySelector("[data-card-shade-name]");
    const swatches = [...card.querySelectorAll("[data-card-swatch]:not(:disabled)")];

    const chooseShade = (swatch) => {
      swatches.forEach((item) => item.classList.toggle("is-selected", item === swatch));
      if (variantInput) variantInput.value = swatch.dataset.variantId || "";
      if (shadeName) shadeName.textContent = swatch.getAttribute("title") || "";
      if (image && swatch.dataset.image) {
        image.classList.add("is-changing");
        image.src = swatch.dataset.image;
        window.setTimeout(() => image.classList.remove("is-changing"), 180);
      }
    };

    swatches.forEach((swatch) => {
      swatch.addEventListener("click", () => chooseShade(swatch));
    });
    if (swatches.length) chooseShade(swatches[0]);
  });

  const variantSelect = document.querySelector("[data-variant-select]");
  const pdpSwatches = [...document.querySelectorAll("[data-pdp-swatch]:not(:disabled)")];
  if (variantSelect && pdpSwatches.length) {
    const pdpImage = document.querySelector("[data-pdp-main-image]");
    const shadeName = document.querySelector("[data-shade-name]");
    const choosePdpShade = (swatch) => {
      pdpSwatches.forEach((item) => item.classList.toggle("is-selected", item === swatch));
      variantSelect.value = swatch.dataset.variantId || "";
      const selected = variantSelect.options[variantSelect.selectedIndex];
      if (shadeName && selected) shadeName.textContent = selected.textContent.replace("(sold out)", "").trim();
      if (pdpImage && swatch.dataset.image) pdpImage.src = swatch.dataset.image;
    };
    pdpSwatches.forEach((swatch) => {
      swatch.addEventListener("click", () => choosePdpShade(swatch));
    });
    variantSelect.addEventListener("change", () => {
      const match = pdpSwatches.find((item) => item.dataset.variantId === variantSelect.value);
      if (match) choosePdpShade(match);
    });
    const selected = pdpSwatches.find((item) => item.dataset.variantId === variantSelect.value);
    choosePdpShade(selected || pdpSwatches[0]);
  }

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduceMotion && "IntersectionObserver" in window) {
    document
      .querySelectorAll(".section, .band, .story-grid, .product-card, .shop-mood-rail, .shade-studio, .mood-chip, .shade-story")
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

  document.querySelectorAll(".auth-form input[type='password']").forEach((input) => {
    if (input.closest(".password-field")) return;

    const wrap = document.createElement("div");
    wrap.className = "password-field";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "password-field__toggle";
    toggle.setAttribute("aria-label", "Show password");
    toggle.setAttribute("aria-pressed", "false");
    toggle.innerHTML =
      '<svg class="password-field__icon password-field__icon--show" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12s-3.5 6.5-9.5 6.5S2.5 12 2.5 12Z"/>' +
      '<circle cx="12" cy="12" r="2.75"/>' +
      "</svg>" +
      '<svg class="password-field__icon password-field__icon--hide" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M3 3l18 18"/>' +
      '<path d="M10.7 10.7a2.75 2.75 0 0 0 3.9 3.9"/>' +
      '<path d="M9.9 5.7A10.4 10.4 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a17.6 17.6 0 0 1-3.3 3.8"/>' +
      '<path d="M6.6 6.6C4.2 8.2 2.5 12 2.5 12s3.5 6.5 9.5 6.5c1.1 0 2.1-.2 3-.5"/>' +
      "</svg>";
    wrap.appendChild(toggle);

    toggle.addEventListener("click", () => {
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      toggle.classList.toggle("is-visible", !showing);
      toggle.setAttribute("aria-pressed", showing ? "false" : "true");
      toggle.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    });
  });

  const idleMs = Number(document.body.dataset.clientIdleMs || 0);
  const idleLogoutForm = document.getElementById("client-idle-logout");
  if (idleMs > 0 && idleLogoutForm) {
    let idleTimer = null;
    const armIdleLogout = () => {
      window.clearTimeout(idleTimer);
      idleTimer = window.setTimeout(() => {
        idleLogoutForm.submit();
      }, idleMs);
    };
    ["pointerdown", "keydown", "mousemove", "scroll", "touchstart", "wheel"].forEach((eventName) => {
      window.addEventListener(eventName, armIdleLogout, { passive: true });
    });
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") armIdleLogout();
    });
    armIdleLogout();
  }

  const bindToast = (toast) => {
    const ms = Number(toast.dataset.toastMs || 4000);
    const dismiss = () => {
      if (toast.classList.contains("is-leaving")) return;
      toast.classList.add("is-leaving");
      window.setTimeout(() => toast.remove(), 280);
    };
    const closeBtn = toast.querySelector("[data-toast-close]");
    if (closeBtn) closeBtn.addEventListener("click", dismiss);
    window.setTimeout(dismiss, Math.max(1200, ms));
  };

  document.querySelectorAll("[data-toast]").forEach(bindToast);

  const ensureToastHost = () => {
    let host = document.querySelector(".site-toasts");
    if (!host) {
      host = document.createElement("div");
      host.className = "site-toasts";
      host.setAttribute("aria-live", "polite");
      host.setAttribute("aria-relevant", "additions");
      document.body.appendChild(host);
    }
    return host;
  };

  const showToast = (message, level = "info", ms = 4200) => {
    if (!message) return;
    const host = ensureToastHost();
    const toast = document.createElement("div");
    const safeLevel = ["success", "error", "warning", "info"].includes(level) ? level : "info";
    toast.className = `site-toast site-toast--${safeLevel}`;
    toast.dataset.toast = "";
    toast.dataset.toastMs = String(ms);
    toast.setAttribute("role", "status");
    toast.innerHTML =
      '<span class="site-toast__mark" aria-hidden="true"></span>' +
      `<p class="site-toast__text"></p>` +
      '<button class="site-toast__close" type="button" data-toast-close aria-label="Dismiss">×</button>';
    toast.querySelector(".site-toast__text").textContent = message;
    host.appendChild(toast);
    bindToast(toast);
  };

  const updateCartCount = (count) => {
    const n = Math.max(0, Number(count) || 0);
    document.querySelectorAll("[data-cart-count]").forEach((el) => {
      el.textContent = String(n);
    });
    document.querySelectorAll("[data-cart-link]").forEach((link) => {
      link.setAttribute("aria-label", `Shopping cart, ${n} items`);
    });
  };

  const isCartAddAction = (action) => {
    if (!action) return false;
    try {
      const path = new URL(action, window.location.origin).pathname;
      return /\/cart\/add\/?$/.test(path) || /\/cart\/add-many\/?$/.test(path);
    } catch (e) {
      return action.includes("/cart/add");
    }
  };

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.dataset.ajaxCart === "off") return;

    const submitter = event.submitter;
    if (submitter && (submitter.name === "buy_now" || submitter.hasAttribute("formaction"))) {
      return;
    }

    const action = form.getAttribute("action") || "";
    if (!isCartAddAction(action)) return;

    const nextInput = form.querySelector('input[name="next"]');
    const nextVal = nextInput ? nextInput.value : "";
    if (nextVal && /checkout/i.test(nextVal)) return;

    event.preventDefault();

    const body = new FormData(form);
    const btn = submitter instanceof HTMLButtonElement ? submitter : form.querySelector('[type="submit"]');
    if (btn) {
      btn.disabled = true;
      btn.classList.add("is-busy");
    }

    fetch(form.action || action, {
      method: "POST",
      body,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        Accept: "application/json",
      },
      credentials: "same-origin",
    })
      .then(async (response) => {
        let data = {};
        try {
          data = await response.json();
        } catch (e) {
          data = {};
        }
        if (typeof data.cart_count !== "undefined") {
          updateCartCount(data.cart_count);
        }
        showToast(
          data.message || (response.ok ? "Added to your cart." : "Could not add to cart."),
          data.level || (response.ok ? "success" : "error"),
          response.ok ? 3200 : 4500
        );
        if (btn) {
          btn.classList.add("is-added");
          window.setTimeout(() => btn.classList.remove("is-added"), 900);
        }
      })
      .catch(() => {
        showToast("Network error — try again.", "error", 4500);
      })
      .finally(() => {
        if (btn) {
          btn.disabled = false;
          btn.classList.remove("is-busy");
        }
      });
  });

  document.querySelectorAll("[data-cart-qty-form]").forEach((form) => {
    const input = form.querySelector("[data-cart-qty]");
    if (!input) return;
    let timer = null;
    const row = form.closest("[data-cart-row]");
    const lineTotal = row ? row.querySelector("[data-cart-line-total]") : null;
    const unitPrice = row ? Number(row.dataset.unitPrice || 0) : 0;
    const currency = input.dataset.currency || "";

    const previewLine = () => {
      if (!lineTotal || !Number.isFinite(unitPrice)) return;
      const qty = Math.max(0, Number(input.value || 0));
      const total = (unitPrice * qty).toFixed(2).replace(/\.00$/, "");
      lineTotal.textContent = `${currency} ${total}`.replace(/\s+/g, " ").trim();
    };

    const submitSoon = () => {
      window.clearTimeout(timer);
      previewLine();
      timer = window.setTimeout(() => form.requestSubmit(), 450);
    };

    input.addEventListener("change", submitSoon);
    input.addEventListener("input", previewLine);
  });

  const orderWa = document.querySelector("[data-order-wa]");
  if (orderWa) {
    const csrfToken = () =>
      document.querySelector("#order-wa-csrf input[name='csrfmiddlewaretoken']")?.value || "";

    orderWa.addEventListener("click", (event) => {
      event.preventDefault();
      const number = orderWa.dataset.waNumber || "";
      const previewUrl = orderWa.dataset.previewUrl || "";
      const clearUrl = orderWa.dataset.clearUrl || "";
      if (!number || !previewUrl) {
        window.open(orderWa.href, "_blank", "noopener,noreferrer");
        return;
      }

      const token = csrfToken();
      if (!token) {
        showToast("Could not verify this request. Refresh and try again.", "error", 4000);
        return;
      }

      const badgeCount = Number(
        document.querySelector("[data-cart-count]")?.textContent?.trim() || "0"
      );
      if (badgeCount > 0) {
        const ok = window.confirm(
          "Open WhatsApp to send your cart as an order? Your cart will be cleared afterward."
        );
        if (!ok) return;
      }

      orderWa.classList.add("is-busy");
      // Keep the popup tied to the click (fetch alone would get blocked).
      const waWindow = window.open("about:blank", "_blank");

      fetch(previewUrl, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": token,
        },
        credentials: "same-origin",
      })
        .then(async (response) => {
          const data = await response.json().catch(() => ({}));
          if (!response.ok || data.ok === false) {
            if (waWindow) waWindow.close();
            showToast(data.message || "Could not prepare your order.", "error", 4000);
            return null;
          }

          const message =
            data.message || "Hi Pretty Affairs Hub — I'd like to place an order.";
          const waUrl = `https://wa.me/${number}?text=${encodeURIComponent(message)}`;
          if (waWindow) {
            waWindow.location = waUrl;
          } else {
            window.location.assign(waUrl);
          }

          if (!data.has_items || !clearUrl) return null;

          return fetch(clearUrl, {
            method: "POST",
            headers: {
              Accept: "application/json",
              "X-Requested-With": "XMLHttpRequest",
              "X-CSRFToken": token,
            },
            credentials: "same-origin",
          }).then(async (clearResponse) => {
            const clearData = await clearResponse.json().catch(() => ({}));
            if (!clearResponse.ok || clearData.ok === false) {
              showToast(clearData.message || "Could not clear cart.", "error", 4000);
              return clearData;
            }
            updateCartCount(0);
            showToast("Order opened in WhatsApp — your cart is cleared.", "success", 4200);
            if (/\/cart\/?$/.test(window.location.pathname)) {
              window.setTimeout(() => window.location.reload(), 500);
            }
            return clearData;
          });
        })
        .catch(() => {
          if (waWindow) {
            try {
              waWindow.close();
            } catch (e) {
              /* ignore */
            }
          }
          showToast("Could not prepare your order. Try again.", "error", 4000);
        })
        .finally(() => {
          orderWa.classList.remove("is-busy");
        });
    });
  }
})();
