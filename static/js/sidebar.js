(function () {
    var STORAGE_KEY = "sidebar_state";

    function readCollapsedPreference() {
        try {
            var state = localStorage.getItem(STORAGE_KEY);
            if (state === "collapsed" || state === "1" || state === "true") {
                return true;
            }
            if (state === "open" || state === "0" || state === "false") {
                return false;
            }
            if (localStorage.getItem("cyberops-sidebar-collapsed") === "1") {
                return true;
            }
        } catch (e) {
            /* ignore */
        }
        return false;
    }

    function writeCollapsedPreference(collapsed) {
        try {
            localStorage.setItem(STORAGE_KEY, collapsed ? "collapsed" : "open");
            localStorage.removeItem("cyberops-sidebar-collapsed");
        } catch (e) {
            /* ignore */
        }
    }

    function initSidebar() {
        var shell = document.getElementById("app-shell");
        var toggle = document.getElementById("sidebar-toggle");
        var backdrop = document.getElementById("sidebar-backdrop");
        var mobileQuery = window.matchMedia("(max-width: 767px)");

        if (!shell || !toggle) {
            return;
        }

        function isMobile() {
            return mobileQuery.matches;
        }

        function applyCollapsed(collapsed) {
            shell.classList.toggle("is-sidebar-collapsed", collapsed);
            shell.setAttribute("data-sidebar-state", collapsed ? "collapsed" : "open");
            document.documentElement.setAttribute("data-sidebar-state", collapsed ? "collapsed" : "open");

            toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
            toggle.setAttribute("aria-label", collapsed ? "Menüyü aç" : "Menüyü kapat");

            var icon = toggle.querySelector(".material-symbols-outlined");
            if (icon) {
                icon.textContent = collapsed ? "menu" : "menu_open";
            }

            if (backdrop) {
                var showBackdrop = !collapsed && isMobile();
                backdrop.classList.toggle("hidden", !showBackdrop);
                backdrop.classList.toggle("is-visible", showBackdrop);
            }

            if (!isMobile()) {
                writeCollapsedPreference(collapsed);
            }
        }

        toggle.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            var next = !shell.classList.contains("is-sidebar-collapsed");
            applyCollapsed(next);
        });

        if (backdrop) {
            backdrop.addEventListener("click", function () {
                if (isMobile()) {
                    applyCollapsed(true);
                }
            });
        }

        var initCollapsed;
        if (isMobile()) {
            initCollapsed = true;
        } else if (document.documentElement.getAttribute("data-sidebar-init") === "collapsed") {
            initCollapsed = true;
            document.documentElement.removeAttribute("data-sidebar-init");
        } else {
            initCollapsed = readCollapsedPreference();
        }
        applyCollapsed(initCollapsed);

        mobileQuery.addEventListener("change", function () {
            if (isMobile()) {
                applyCollapsed(true);
            } else {
                applyCollapsed(readCollapsedPreference());
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initSidebar);
    } else {
        initSidebar();
    }
})();
