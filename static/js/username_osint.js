document.addEventListener("DOMContentLoaded", () => {
    const root = document.querySelector(".page-username-osint");
    if (!root) return;

    root.querySelectorAll("[data-account-tab]").forEach((tab) => {
        tab.addEventListener("click", () => {
            const target = tab.getAttribute("data-account-tab");
            root.querySelectorAll("[data-account-tab]").forEach((t) => t.classList.toggle("is-active", t === tab));
            root.querySelectorAll("[data-account-panel]").forEach((panel) => {
                panel.classList.toggle("is-active", panel.getAttribute("data-account-panel") === target);
            });
        });
    });

    let activeCategory = "all";
    const applyCategoryFilter = () => {
        root.querySelectorAll("[data-category-row]").forEach((row) => {
            const cat = row.getAttribute("data-category-row");
            row.classList.toggle("is-hidden", activeCategory !== "all" && cat !== activeCategory);
        });
    };

    root.querySelectorAll("[data-cat-filter]").forEach((btn) => {
        btn.addEventListener("click", () => {
            activeCategory = btn.getAttribute("data-cat-filter") || "all";
            root.querySelectorAll("[data-cat-filter]").forEach((b) => b.classList.toggle("is-active", b === btn));
            applyCategoryFilter();
        });
    });
});
