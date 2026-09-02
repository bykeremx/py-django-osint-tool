document.addEventListener("DOMContentLoaded", () => {
    const root = document.querySelector(".page-email-osint");
    if (!root) return;

    const tabs = root.querySelectorAll("[data-account-tab]");
    const panels = root.querySelectorAll("[data-account-panel]");

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const target = tab.getAttribute("data-account-tab");
            tabs.forEach((t) => t.classList.toggle("is-active", t === tab));
            panels.forEach((panel) => {
                panel.classList.toggle("is-active", panel.getAttribute("data-account-panel") === target);
            });
        });
    });
});
