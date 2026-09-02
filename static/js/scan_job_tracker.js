(function () {
    var activeUrl = window.SCAN_JOBS_ACTIVE_URL;
    if (!activeUrl) {
        return;
    }

    var track = document.getElementById("topbar-ops-track");
    var idle = document.getElementById("topbar-ops-idle");
    var pendingBadge = document.getElementById("topbar-pending-badge");
    var pendingCount = document.getElementById("topbar-pending-count");
    var pollMs = 3000;
    var cancelling = {};

    if (!track || !idle || !pendingBadge || !pendingCount) {
        return;
    }

    function getCsrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) {
            return meta.content;
        }
        var name = "csrftoken=";
        var parts = document.cookie.split(";");
        for (var i = 0; i < parts.length; i++) {
            var part = parts[i].trim();
            if (part.indexOf(name) === 0) {
                return decodeURIComponent(part.substring(name.length));
            }
        }
        return "";
    }

    function parseJsonResponse(res) {
        return res.text().then(function (text) {
            if (!text) {
                return {};
            }
            try {
                return JSON.parse(text);
            } catch (error) {
                return { error: res.status === 403 ? "CSRF doğrulaması başarısız. Sayfayı yenileyip tekrar deneyin." : "Sunucu yanıtı okunamadı." };
            }
        });
    }

    function cancelUrl(jobId) {
        if (window.SCAN_JOB_CANCEL_URL) {
            return window.SCAN_JOB_CANCEL_URL.replace("__JOB_ID__", encodeURIComponent(jobId));
        }
        return "/scan-job/" + encodeURIComponent(jobId) + "/cancel/";
    }

    function cancelAllUrl() {
        return window.SCAN_JOBS_CANCEL_ALL_URL || "/scan-job/cancel-all/";
    }

    function statusLabel(status) {
        if (status === "pending") return "Çalışıyor";
        if (status === "finished") return "Tamam";
        if (status === "failed") return "Hata";
        if (status === "cancelled") return "İptal";
        return "—";
    }

    function shortModule(label) {
        if (!label) return "SCAN";
        var parts = label.split(" ");
        return parts.length > 1 ? parts[0] : label.slice(0, 8);
    }

    function cancelJob(jobId) {
        if (!jobId || cancelling[jobId]) {
            return Promise.resolve();
        }
        cancelling[jobId] = true;
        var csrf = getCsrfToken();
        if (!csrf) {
            window.alert("Güvenlik anahtarı bulunamadı. Sayfayı yenileyip tekrar deneyin.");
            delete cancelling[jobId];
            return Promise.resolve();
        }
        return fetch(cancelUrl(jobId), {
            method: "POST",
            headers: {
                Accept: "application/json",
                "Content-Type": "application/json",
                "X-CSRFToken": csrf,
            },
            credentials: "same-origin",
        })
            .then(function (res) {
                return parseJsonResponse(res).then(function (data) {
                    return { ok: res.ok, data: data };
                });
            })
            .then(function (result) {
                if (!result.ok) {
                    window.alert((result.data && result.data.error) || "İptal isteği reddedildi.");
                }
                return refresh();
            })
            .catch(function () {
                window.alert("İptal isteği gönderilemedi.");
            })
            .finally(function () {
                delete cancelling[jobId];
            });
    }

    function cancelAllPending() {
        if (!window.confirm("Bekleyen tüm taramalar iptal edilsin mi?")) {
            return Promise.resolve();
        }
        return fetch(cancelAllUrl(), {
            method: "POST",
            headers: {
                Accept: "application/json",
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            credentials: "same-origin",
        })
            .then(function (res) {
                return parseJsonResponse(res);
            })
            .then(function () {
                return refresh();
            })
            .catch(function () {
                window.alert("Toplu iptal isteği gönderilemedi.");
            });
    }

    window.cyberOpsCancelScanJob = cancelJob;
    window.cyberOpsCancelAllScanJobs = cancelAllPending;

    function renderCancelButton(jobId) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "ops-chip__cancel";
        btn.title = "İptal et";
        btn.setAttribute("aria-label", "Taramayı iptal et");
        btn.innerHTML = '<span class="material-symbols-outlined">close</span>';
        btn.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            cancelJob(jobId);
        });
        return btn;
    }

    function renderChip(job) {
        var status = job.status || "pending";
        var el;

        if (status === "finished" && job.result_url) {
            el = document.createElement("a");
            el.href = job.result_url;
            el.className = "ops-chip ops-chip--finished";
        } else {
            el = document.createElement("div");
            el.className = "ops-chip ops-chip--" + status;
        }

        var mod = document.createElement("span");
        mod.className = "ops-chip__module";
        mod.textContent = shortModule(job.module_label || job.module);

        var target = document.createElement("span");
        target.className = "ops-chip__target";
        target.textContent = job.target || "—";
        target.title = job.target || "";

        var st = document.createElement("span");
        st.className = "ops-chip__status is-" + status;

        if (status === "pending") {
            var spin = document.createElement("span");
            spin.className = "ops-chip__spinner";
            spin.setAttribute("aria-hidden", "true");
            st.appendChild(spin);
        }

        var stText = document.createElement("span");
        stText.textContent = statusLabel(status);
        st.appendChild(stText);

        el.appendChild(mod);
        el.appendChild(target);
        el.appendChild(st);

        if (status === "pending" && job.job_id) {
            el.appendChild(renderCancelButton(job.job_id));
        }

        if (status === "finished") {
            var arrow = document.createElement("span");
            arrow.className = "material-symbols-outlined ops-chip__arrow";
            arrow.textContent = "arrow_forward";
            el.appendChild(arrow);
        }

        if (status === "failed" && job.error) {
            el.title = job.error;
        }

        return el;
    }

    function renderJobs(jobs, pending) {
        track.innerHTML = "";

        if (!jobs.length) {
            idle.hidden = false;
            track.hidden = true;
            pendingBadge.hidden = true;
            return;
        }

        idle.hidden = true;
        track.hidden = false;
        pendingBadge.hidden = pending === 0;
        pendingCount.textContent = String(pending);

        jobs.forEach(function (job) {
            track.appendChild(renderChip(job));
        });
    }

    function refresh() {
        return fetch(activeUrl, {
            headers: { Accept: "application/json" },
            credentials: "same-origin",
        })
            .then(function (res) {
                return res.json();
            })
            .then(function (data) {
                var jobs = data.jobs || [];
                var pending = data.pending_count || 0;
                renderJobs(jobs, pending);
                document.dispatchEvent(
                    new CustomEvent("scanJobsUpdated", {
                        detail: { jobs: jobs, pending_count: pending },
                    })
                );
                if (pending > 0) {
                    window.setTimeout(refresh, pollMs);
                }
            })
            .catch(function () {
                window.setTimeout(refresh, pollMs * 2);
            });
    }

    document.addEventListener("click", function (event) {
        var btn = event.target.closest("[data-scan-cancel]");
        if (!btn) {
            return;
        }
        event.preventDefault();
        var jobId = btn.getAttribute("data-scan-cancel");
        if (jobId) {
            cancelJob(jobId);
        }
    });

    document.addEventListener("click", function (event) {
        var btn = event.target.closest("[data-scan-cancel-all]");
        if (!btn) {
            return;
        }
        event.preventDefault();
        cancelAllPending();
    });

    refresh();
    window.setInterval(refresh, pollMs * 4);
})();
