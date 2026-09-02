(function () {
    var STORAGE_KEY = "cyberops_theme";

    function getPreferred() {
        try {
            var saved = localStorage.getItem(STORAGE_KEY);
            if (saved === "light" || saved === "dark") {
                return saved;
            }
        } catch (e) {
            /* ignore */
        }
        return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    }

    function applyTheme(theme) {
        var next = theme === "light" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        try {
            localStorage.setItem(STORAGE_KEY, next);
        } catch (e) {
            /* ignore */
        }

        var btn = document.getElementById("theme-toggle");
        if (!btn) {
            return;
        }
        var icon = btn.querySelector(".material-symbols-outlined");
        var isLight = next === "light";
        btn.setAttribute("aria-label", isLight ? "Koyu moda geç" : "Açık moda geç");
        btn.setAttribute("title", isLight ? "Dark mode" : "Light mode");
        if (icon) {
            icon.textContent = isLight ? "dark_mode" : "light_mode";
        }
    }

    function initThemeToggle() {
        var btn = document.getElementById("theme-toggle");
        if (!btn) {
            return;
        }
        applyTheme(document.documentElement.getAttribute("data-theme") || getPreferred());
        btn.addEventListener("click", function () {
            var current = document.documentElement.getAttribute("data-theme") || "dark";
            applyTheme(current === "light" ? "dark" : "light");
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initThemeToggle);
    } else {
        initThemeToggle();
    }

    window.CyberOpsTheme = { applyTheme: applyTheme, getPreferred: getPreferred };
})();
