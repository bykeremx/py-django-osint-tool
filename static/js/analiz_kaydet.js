(function () {
    function getCookie(name) {
        const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
        return match ? decodeURIComponent(match[2]) : "";
    }

    function downloadJson(filename, data) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(url);
    }

    function updateEmptyState(listEl, emptyEl) {
        if (!listEl || !emptyEl) return;
        emptyEl.style.display = listEl.children.length ? "none" : "block";
    }

    function addItemRow(listEl, emptyEl, template) {
        if (!listEl || !template) return;
        const node = template.content.cloneNode(true);
        const row = node.querySelector(".analiz-item-row");
        const removeBtn = row.querySelector(".analiz-item-remove");
        removeBtn.addEventListener("click", () => {
            row.remove();
            updateEmptyState(listEl, emptyEl);
        });
        listEl.appendChild(node);
        updateEmptyState(listEl, emptyEl);
        const keyInput = listEl.lastElementChild.querySelector(".analiz-item-key");
        if (keyInput) keyInput.focus();
    }

    function collectItems(listEl) {
        const items = [];
        if (!listEl) return items;
        listEl.querySelectorAll(".analiz-item-row").forEach((row) => {
            const key = (row.querySelector(".analiz-item-key")?.value || "").trim();
            const value = (row.querySelector(".analiz-item-value")?.value || "").trim();
            if (key && value) items.push({ key, value });
        });
        return items;
    }

    document.querySelectorAll(".analiz-save-panel").forEach((panel) => {
        const listEl = panel.querySelector(".analiz-items-list");
        const emptyEl = panel.querySelector(".analiz-items-empty");
        const template = panel.querySelector(".analiz-item-row-template");
        const addBtn = panel.querySelector("[data-analiz-add-item]");

        if (addBtn && listEl && template) {
            addBtn.addEventListener("click", () => addItemRow(listEl, emptyEl, template));
        }
        updateEmptyState(listEl, emptyEl);
    });

    document.querySelectorAll("[data-analiz-save]").forEach((button) => {
        button.addEventListener("click", async () => {
            const panel = button.closest(".analiz-save-panel");
            const statusEl = panel ? panel.querySelector(".analiz-save-status") : null;
            const noteEl = panel ? panel.querySelector(".analiz-analyst-note") : null;
            const dataNode = document.getElementById("analiz-report-data");
            const listEl = panel ? panel.querySelector(".analiz-items-list") : null;

            if (!dataNode) {
                if (statusEl) {
                    statusEl.textContent = "Rapor verisi yok.";
                    statusEl.className = "analiz-save-status is-error";
                }
                return;
            }

            let report;
            try {
                report = JSON.parse(dataNode.textContent);
            } catch (_) {
                if (statusEl) {
                    statusEl.textContent = "Rapor okunamadı.";
                    statusEl.className = "analiz-save-status is-error";
                }
                return;
            }

            const module = button.getAttribute("data-analiz-module") || "";
            const target = button.getAttribute("data-analiz-target") || "";
            const note = noteEl ? noteEl.value.trim() : "";
            const items = collectItems(listEl);

            if (statusEl) {
                statusEl.textContent = "Kaydediliyor…";
                statusEl.className = "analiz-save-status";
            }
            button.disabled = true;

            try {
                const response = await fetch("/analiz/kaydet/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCookie("csrftoken"),
                    },
                    body: JSON.stringify({ module, target, note, report, items }),
                });
                const result = await response.json();

                if (!response.ok || !result.ok) {
                    throw new Error(result.error || "Kayıt başarısız.");
                }

                const exportData = result.export || report;
                const safeTarget = (target || "hedef").replace(/[^\w.-]+/g, "_");
                downloadJson(`analiz-${module}-${safeTarget}-${result.id}.json`, exportData);

                if (statusEl) {
                    statusEl.innerHTML =
                        (result.message || "Kaydedildi") +
                        ' · <a href="' +
                        result.detail_url +
                        '">Detay</a>';
                    statusEl.className = "analiz-save-status is-success";
                }
            } catch (err) {
                if (statusEl) {
                    statusEl.textContent = err.message || "Hata.";
                    statusEl.className = "analiz-save-status is-error";
                }
            } finally {
                button.disabled = false;
            }
        });
    });
})();
