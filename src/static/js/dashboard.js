// src/static/js/dashboard.js - Dashboard tab logic

const API_ENDPOINTS = [
    { method: "GET",  path: "/v1/models", desc: "List available models" },
    { method: "POST", path: "/v1/chat/completions", desc: "Chat completions — OpenAI format" },
    { method: "POST", path: "/v1beta/models/{model}", desc: "Generate content — Google AI format" },
    { method: "POST", path: "/gemini", desc: "Generate content — simple JSON format" },
    { method: "POST", path: "/gemini-chat", desc: "Chat with context — simple JSON format" },
];

const Dashboard = {
    intervalId: null,

    init() {
        document.getElementById("btn-reinit").addEventListener("click", async () => {
            const btn = document.getElementById("btn-reinit");
            const resultEl = document.getElementById("reinit-result");
            btn.disabled = true;
            btn.textContent = "Reinitializing...";
            try {
                const data = await api.post("/api/admin/client/reinitialize");
                if (data.success) {
                    showInline(resultEl, data.message, false);
                } else {
                    resultEl.innerHTML = buildErrorMessage(data);
                    resultEl.style.color = "var(--error)";
                }
            } catch (err) {
                showInline(resultEl, "Failed: " + (err.detail || "Unknown error"), true);
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
        const statusCard = document.getElementById("card-status");
        if (data.gemini_status === "connected") {
            statusEl.textContent = "Connected";
            statusEl.style.color = "var(--success)";
            statusCard.querySelector(".stat-detail")?.remove();
        } else {
            statusEl.textContent = "Disconnected";
            statusEl.style.color = "var(--error)";
            // Show error hint under status card
            let detailEl = statusCard.querySelector(".stat-detail");
            if (!detailEl) {
                detailEl = document.createElement("div");
                detailEl.className = "stat-detail";
                statusCard.appendChild(detailEl);
            }
            const hints = {
                auth_expired: "Cookie expired — get fresh cookies",
                no_cookies: "No cookies — go to Configuration tab",
                network: "Network error — check connection/proxy",
                disabled: "Gemini disabled in config",
            };
            detailEl.innerHTML = `<span class="error">${escapeHtml(hints[data.error_code] || data.client_error || "Check Configuration tab")}</span>`;
        }

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
        document.getElementById("api-base-url").textContent = baseUrl + "/v1";

        const tbody = document.getElementById("api-ref-tbody");
        tbody.innerHTML = API_ENDPOINTS.map(ep => {
            const fullUrl = baseUrl + ep.path;
            return `<tr>
                <td><span class="method-badge method-${ep.method.toLowerCase()}">${ep.method}</span></td>
                <td><code class="api-url">${escapeHtml(fullUrl)}</code></td>
                <td class="api-desc">${escapeHtml(ep.desc)}</td>
                <td><button class="btn btn-small btn-copy" data-copy-value="${escapeHtml(fullUrl)}" title="Copy URL">Copy</button></td>
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
