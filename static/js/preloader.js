(function () {
    const preloader = document.getElementById("preloader");
    if (!preloader) return;

    const STORAGE_KEY = "cyberops_queue_nav";
    const terminal = document.getElementById("preloader-terminal");
    const statusEl = document.getElementById("preloader-status");
    const progressBar = document.getElementById("preloader-progress-bar");
    const progressPct = document.getElementById("preloader-progress-pct");

    const LOG_LINES = [
        { text: "OpenSSL 3.x — cipher suite: AES-256-GCM", cls: "sys" },
        { text: "export RECON_MODE=passive_aggressive", cls: "cmd" },
        { text: "Loading modules: dns, network, nmap, osint…", cls: "sys" },
        { text: "Redis queue channel [OK]", cls: "ok" },
        { text: "MySQL telemetry sync [OK]", cls: "ok" },
        { text: "Bypassing honeypot signatures… (sim)", cls: "warn" },
        { text: "Sherlock / Maigret / Holehe engines ready", cls: "ok" },
        { text: "WHOIS · RDAP · Wappalyzer pipeline armed", cls: "ok" },
        { text: "iptables: DROP unauthorized egress [sim]", cls: "cmd" },
        { text: "Session nonce: " + randomHex(8), cls: "sys" },
        { text: "Threat feed delta: +0 IOC (clean)", cls: "ok" },
        { text: "Operator clearance: ANALYST verified", cls: "ok" },
    ];

    const STATUS_LINES = [
        "[ INIT ] Şifreli kanal kuruluyor…",
        "[ SYNC ] OSINT modülleri yükleniyor…",
        "[ SCAN ] Tehdit yüzeyi haritalanıyor…",
        "[ LINK ] Güvenli tünel aktif…",
        "[ RUN  ] Recon pipeline hazır…",
        "[ OK   ] Sistem online — erişim onaylandı",
    ];

    let animTimer = null;
    let progressTimer = null;
    let lineIndex = 0;
    let statusIndex = 0;

    function randomHex(len) {
        var s = "";
        for (var i = 0; i < len; i++) {
            s += Math.floor(Math.random() * 16).toString(16);
        }
        return s;
    }

    function hide() {
        stopAnimation();
        preloader.classList.add("is-hidden");
    }

    function show() {
        preloader.classList.remove("is-hidden");
        startAnimation();
    }

    function stopAnimation() {
        if (animTimer) {
            clearInterval(animTimer);
            animTimer = null;
        }
        if (progressTimer) {
            clearInterval(progressTimer);
            progressTimer = null;
        }
    }

    function addTerminalLine(entry) {
        if (!terminal) return;
        var line = document.createElement("div");
        line.className = "preloader-terminal__line preloader-terminal__line--" + (entry.cls || "sys");
        line.innerHTML =
            '<span class="preloader-terminal__prompt">›</span>' +
            entry.text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        terminal.appendChild(line);

        while (terminal.children.length > 6) {
            terminal.removeChild(terminal.firstChild);
        }
    }

    function setProgress(pct) {
        var v = Math.min(100, Math.max(0, pct));
        if (progressBar) progressBar.style.width = v + "%";
        if (progressPct) progressPct.textContent = Math.round(v) + "%";
        var wrap = preloader.querySelector(".preloader-progress");
        if (wrap) wrap.setAttribute("aria-valuenow", String(Math.round(v)));
    }

    function startAnimation() {
        stopAnimation();
        if (terminal) terminal.innerHTML = "";
        lineIndex = 0;
        statusIndex = 0;
        setProgress(0);

        addTerminalLine({ text: "CYBER OPS secure boot v2.6.0", cls: "cmd" });
        addTerminalLine({ text: "kernel: Linux x86_64 · target: recon_console", cls: "sys" });

        var progress = 8;
        progressTimer = setInterval(function () {
            if (progress < 92) {
                progress += Math.random() * 6 + 2;
                setProgress(progress);
            }
        }, 180);

        animTimer = setInterval(function () {
            if (lineIndex < LOG_LINES.length) {
                addTerminalLine(LOG_LINES[lineIndex]);
                lineIndex += 1;
            }
            if (statusEl) {
                statusEl.textContent = STATUS_LINES[statusIndex % STATUS_LINES.length];
                statusIndex += 1;
            }
        }, 420);
    }

    try {
        if (sessionStorage.getItem(STORAGE_KEY) === "1") {
            sessionStorage.removeItem(STORAGE_KEY);
            hide();
        } else {
            startAnimation();
        }
    } catch (e) {
        startAnimation();
    }

    window.addEventListener("load", function () {
        setProgress(100);
        setTimeout(hide, 550);
    });

    function isQueueScanForm(form) {
        return (
            form instanceof HTMLFormElement &&
            (form.classList.contains("scan-queue-form") || form.hasAttribute("data-scan-queue"))
        );
    }

    function setQueueSubmitting(form) {
        hide();

        var btn = form.querySelector('[type="submit"]');
        if (!btn || btn.dataset.queueSubmitting === "1") {
            return;
        }
        btn.dataset.queueSubmitting = "1";
        btn.dataset.originalLabel = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML =
            '<span class="material-symbols-outlined text-base animate-spin">progress_activity</span> Kuyruğa alınıyor…';

        var toast = document.getElementById("queue-submit-toast");
        if (toast) {
            toast.hidden = false;
            toast.setAttribute("aria-live", "polite");
        }

        try {
            sessionStorage.setItem(STORAGE_KEY, "1");
        } catch (e) {
            /* ignore */
        }
    }

    document.addEventListener(
        "submit",
        function (event) {
            var form = event.target;
            if (isQueueScanForm(form)) {
                setQueueSubmitting(form);
                return;
            }
            show();
        },
        true
    );

    document.querySelectorAll("a[href]").forEach(function (link) {
        link.addEventListener("click", function (event) {
            if (event.metaKey || event.ctrlKey || link.target === "_blank") return;
            var href = link.getAttribute("href") || "";
            if (href.startsWith("#")) return;
            show();
        });
    });

    window.CyberOpsPreloader = { show: show, hide: hide };
})();
