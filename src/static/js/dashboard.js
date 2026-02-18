// src/static/js/dashboard.js - Dashboard tab logic

const API_ENDPOINTS = [
    { method: "POST", path: "/v1/chat/completions", desc: "OpenAI-compatible chat completions" },
    { method: "POST", path: "/gemini", desc: "Stateless content generation" },
    { method: "POST", path: "/gemini-chat", desc: "Stateful chat with context" },
    { method: "POST", path: "/translate", desc: "Translation (alias for gemini-chat)" },
    { method: "POST", path: "/v1beta/models/{model}", desc: "Google Generative AI format" },
    { method: "GET",  path: "/docs", desc: "Swagger / OpenAPI documentation" },
];

const Dashboard = {
    intervalId: null,

    init() {
        document.getElementById("btn-reinit").addEventListener("click", async () => {
            const btn = document.getElementById("btn-reinit");
            const result = document.getElementById("reinit-result");
            btn.disabled = true;
            btn.textContent = "Reinitializing...";
            try {
                const data = await api.post("/api/admin/client/reinitialize");
                showInline(result, data.message, !data.success);
            } catch (err) {
                showInline(result, "Failed: " + (err.detail || "Unknown error"), true);
            } finally {
                btn.disabled = false;
                btn.textContent = "Reinitialize Gemini Client";
                this.refresh();
            }
        });

        // Render API Reference (static, only once)
        this.renderApiReference();

        // Copy button handlers
        document.querySelectorAll(".btn-copy").forEach(btn => {
            btn.addEventListener("click", () => {
                const targetId = btn.dataset.copyTarget;
                const el = document.getElementById(targetId);
                if (!el) return;
                const text = el.textContent;
                navigator.clipboard.writeText(text).then(() => {
                    const orig = btn.textContent;
                    btn.textContent = "Copied!";
                    btn.classList.add("copied");
                    setTimeout(() => { btn.textContent = orig; btn.classList.remove("copied"); }, 1500);
                });
            });
        });
    },

    activate() {
        this.refresh();
        this.intervalId = setInterval(() => this.refresh(), 10000);
    },

    deactivate() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    },

    async refresh() {
        try {
            const data = await api.get("/api/admin/status");
            this.updateCards(data);
            this.updateEndpointTable(data.stats.endpoints);
        } catch {
            document.getElementById("val-status").textContent = "Error";
        }
    },

    updateCards(data) {
        const statusEl = document.getElementById("val-status");
        statusEl.textContent = data.gemini_status === "connected" ? "Connected" : "Disconnected";
        statusEl.style.color = data.gemini_status === "connected" ? "var(--success)" : "var(--error)";

        document.getElementById("val-model").textContent = data.current_model || "--";
        document.getElementById("val-requests").textContent = data.stats.total_requests;
        document.getElementById("val-success").textContent = data.stats.success_count + " OK";
        document.getElementById("val-errors").textContent = data.stats.error_count + " ERR";
        document.getElementById("val-uptime").textContent = data.stats.uptime;

        // Update header badge
        const badge = document.getElementById("connection-status");
        badge.textContent = data.gemini_status === "connected" ? "Connected" : "Disconnected";
        badge.className = "status-badge " + data.gemini_status;
    },

    updateEndpointTable(endpoints) {
        const tbody = document.getElementById("endpoint-tbody");
        const noData = document.getElementById("no-endpoints");
        const entries = Object.entries(endpoints || {});

        if (entries.length === 0) {
            tbody.innerHTML = "";
            noData.classList.remove("hidden");
            return;
        }

        noData.classList.add("hidden");
        entries.sort((a, b) => b[1] - a[1]);
        tbody.innerHTML = entries
            .map(([path, count]) => `<tr><td>${escapeHtml(path)}</td><td>${count}</td></tr>`)
            .join("");
    },

    getBaseUrl() {
        return window.location.origin;
    },

    renderApiReference() {
        const baseUrl = this.getBaseUrl();
        document.getElementById("api-base-url").textContent = baseUrl;

        const tbody = document.getElementById("api-ref-tbody");
        tbody.innerHTML = API_ENDPOINTS.map(ep => {
            const fullUrl = baseUrl + ep.path;
            const urlId = "url-" + ep.path.replace(/[^a-zA-Z0-9]/g, "-");
            return `<tr>
                <td><span class="method-badge method-${ep.method.toLowerCase()}">${ep.method}</span></td>
                <td><code id="${urlId}" class="api-url">${escapeHtml(ep.path)}</code></td>
                <td class="api-desc">${escapeHtml(ep.desc)}</td>
                <td><button class="btn btn-small btn-copy" data-copy-value="${escapeHtml(fullUrl)}" title="Copy full URL">Copy</button></td>
            </tr>`;
        }).join("");

        // Attach click handlers for dynamically created copy buttons
        tbody.querySelectorAll(".btn-copy").forEach(btn => {
            btn.addEventListener("click", () => {
                const text = btn.dataset.copyValue;
                navigator.clipboard.writeText(text).then(() => {
                    const orig = btn.textContent;
                    btn.textContent = "Copied!";
                    btn.classList.add("copied");
                    setTimeout(() => { btn.textContent = orig; btn.classList.remove("copied"); }, 1500);
                });
            });
        });
    },
};
