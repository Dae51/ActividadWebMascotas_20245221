(() => {
    "use strict";

    if (document.body.dataset.authenticated !== "true") {
        return;
    }

    const badge = document.getElementById("notif-badge");
    const toastRoot = document.getElementById("toast-root");

    const RECONNECT_DELAY_MS = 5000;
    let reconnectTimer = null;
    let stopped = false;

    function renderBadge(unread) {
        if (!badge) {
            return;
        }
        badge.textContent = unread > 99 ? "99+" : String(unread);
        badge.hidden = unread === 0;
    }

    async function refreshBadge() {
        try {
            const response = await fetch("/api/notifications", {
                headers: { Accept: "application/json" },
            });
            if (!response.ok) {
                return;
            }
            const data = await response.json();
            renderBadge(data.unread || 0);
        } catch (error) {
            /* badge refresh is best effort */
        }
    }

    function showToast(payload) {
        if (!toastRoot) {
            return;
        }
        const toast = document.createElement("article");
        toast.className = "toast";

        const title = document.createElement("strong");
        title.textContent = payload.title || "Nuevo aviso";

        const body = document.createElement("p");
        body.textContent = payload.message || "";

        toast.append(title, body);
        toastRoot.appendChild(toast);

        window.setTimeout(() => {
            toast.classList.add("toast-out");
            window.setTimeout(() => toast.remove(), 300);
        }, 6000);
    }

    function scheduleReconnect() {
        if (stopped || reconnectTimer) {
            return;
        }
        reconnectTimer = window.setTimeout(() => {
            reconnectTimer = null;
            connect();
        }, RECONNECT_DELAY_MS);
    }

    async function connect() {
        if (stopped) {
            return;
        }

        let credentials;
        try {
            const response = await fetch("/api/ws-ticket", {
                headers: { Accept: "application/json" },
            });
            if (!response.ok) {
                scheduleReconnect();
                return;
            }
            credentials = await response.json();
        } catch (error) {
            scheduleReconnect();
            return;
        }

        let socket;
        try {
            socket = new WebSocket(credentials.url);
        } catch (error) {
            scheduleReconnect();
            return;
        }

        socket.addEventListener("open", () => {
            socket.send(JSON.stringify({ ticket: credentials.ticket }));
        });

        socket.addEventListener("message", (event) => {
            let payload;
            try {
                payload = JSON.parse(event.data);
            } catch (error) {
                return;
            }
            showToast(payload);
            refreshBadge();
        });

        socket.addEventListener("close", () => {
            scheduleReconnect();
        });

        window.addEventListener(
            "pagehide",
            () => {
                stopped = true;
                if (reconnectTimer) {
                    window.clearTimeout(reconnectTimer);
                }
                socket.close();
            },
            { once: true }
        );
    }

    refreshBadge();
    connect();
})();
