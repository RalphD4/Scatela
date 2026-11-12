(function () {
    const STATUS_COLORS = {
        normal: "#16a34a",
        warning: "#d97706",
        danger: "#dc2626",
        stale: "#64748b",
        no_location: "#64748b",
        no_bases: "#64748b",
    };

    let map = null;
    let layerGroup = null;
    let hasCenteredOnce = false;
    let refreshing = false;

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") : "";
    }

    function formatTime(isoString) {
        if (!isoString) {
            return "Never";
        }
        if (window.ScatelaTracker && window.ScatelaTracker.formatLocalTime) {
            return window.ScatelaTracker.formatLocalTime(isoString);
        }
        return isoString;
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text == null ? "" : String(text);
        return div.innerHTML;
    }

    function initMap(data) {
        const mapEl = document.getElementById("dashboard-map");
        if (!mapEl || typeof L === "undefined") {
            return;
        }

        let initialLat = 37.3382;
        let initialLon = -121.8863;
        if (data.guardian && data.guardian.latitude != null && data.guardian.longitude != null) {
            initialLat = data.guardian.latitude;
            initialLon = data.guardian.longitude;
        } else if (data.bases && data.bases.length > 0) {
            initialLat = data.bases[0].latitude;
            initialLon = data.bases[0].longitude;
        } else if (data.children && data.children.length > 0 && data.children[0].latitude != null) {
            initialLat = data.children[0].latitude;
            initialLon = data.children[0].longitude;
        }

        map = L.map("dashboard-map").setView([initialLat, initialLon], 13);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(map);
        layerGroup = L.layerGroup().addTo(map);
    }

    function renderMapLayers(data) {
        if (!map || !layerGroup) {
            return;
        }
        layerGroup.clearLayers();
        const bounds = [];

        if (data.guardian && data.guardian.latitude != null && data.guardian.longitude != null) {
            const gLatLng = [data.guardian.latitude, data.guardian.longitude];
            bounds.push(gLatLng);
            L.circleMarker(gLatLng, {
                radius: 9,
                color: "#1d4ed8",
                fillColor: "#3b82f6",
                fillOpacity: 0.9,
                weight: 2,
            })
                .bindPopup(
                    `<strong>You (${escapeHtml(data.guardian.username)})</strong><br>Updated: ${escapeHtml(formatTime(data.guardian.location_updated_at))}`
                )
                .addTo(layerGroup);
        }

        (data.bases || []).forEach((base) => {
            if (base.latitude == null || base.longitude == null) {
                return;
            }
            const center = [base.latitude, base.longitude];
            bounds.push(center);

            L.circle(center, {
                radius: base.danger_radius,
                color: "#dc2626",
                fillColor: "#ef4444",
                fillOpacity: 0.08,
                weight: 1.5,
            }).addTo(layerGroup);

            L.circle(center, {
                radius: base.warning_radius,
                color: "#d97706",
                fillColor: "#f59e0b",
                fillOpacity: 0.12,
                weight: 1.5,
            }).addTo(layerGroup);

            L.marker(center)
                .bindPopup(
                    `<strong>Base: ${escapeHtml(base.base_name)}</strong><br>Warning: ${base.warning_radius}m · Danger: ${base.danger_radius}m`
                )
                .addTo(layerGroup);
        });

        (data.children || []).forEach((child) => {
            if (child.latitude == null || child.longitude == null) {
                return;
            }
            const pos = [child.latitude, child.longitude];
            bounds.push(pos);
            const color = STATUS_COLORS[child.monitoring_status] || "#64748b";
            L.circleMarker(pos, {
                radius: 8,
                color: "#ffffff",
                fillColor: color,
                fillOpacity: 0.95,
                weight: 2,
            })
                .bindPopup(
                    `<strong>${escapeHtml(child.username)}</strong><br>Status: ${escapeHtml(child.status_label)}<br>Updated: ${escapeHtml(formatTime(child.location_updated_at))}`
                )
                .addTo(layerGroup);
        });

        if (!hasCenteredOnce && bounds.length > 0) {
            if (bounds.length === 1) {
                map.setView(bounds[0], 14);
            } else {
                map.fitBounds(bounds, { padding: [30, 30] });
            }
            hasCenteredOnce = true;
        }
    }

    function renderGuardianCard(guardian) {
        const coordsEl = document.getElementById("guardian-coords");
        const timeEl = document.getElementById("guardian-updated-at");
        const freshEl = document.getElementById("guardian-fresh-badge");
        if (coordsEl) {
            coordsEl.textContent =
                guardian.latitude != null && guardian.longitude != null
                    ? `${Number(guardian.latitude).toFixed(5)}, ${Number(guardian.longitude).toFixed(5)}`
                    : "Awaiting location";
        }
        if (timeEl) {
            timeEl.textContent = guardian.location_updated_at
                ? `Updated ${formatTime(guardian.location_updated_at)}`
                : "No timestamp recorded yet";
        }
        if (freshEl) {
            if (guardian.location_fresh) {
                freshEl.className = "badge badge-normal";
                freshEl.textContent = "Current";
            } else if (guardian.location_updated_at) {
                freshEl.className = "badge badge-stale";
                freshEl.textContent = "Stale";
            } else {
                freshEl.className = "badge badge-no_location";
                freshEl.textContent = "Pending";
            }
        }
    }

    function renderAlerts(alerts) {
        const container = document.getElementById("alerts-container");
        const countEl = document.getElementById("active-alerts-count");
        if (countEl) {
            countEl.textContent = String(alerts.length);
        }
        if (!container) {
            return;
        }

        if (!alerts.length) {
            container.innerHTML = `<p class="muted">No active alerts. All monitored children with current locations are within thresholds.</p>`;
            return;
        }

        container.innerHTML = alerts
            .map(
                (alert) => `
            <div class="alert-item ${escapeHtml(alert.alert_type)}">
                <div>
                    <div>
                        <span class="badge badge-${escapeHtml(alert.alert_type)}">${escapeHtml(alert.alert_type)}</span>
                        <strong>${escapeHtml(alert.child_username || "Child")}</strong>
                        &mdash; Base: <strong>${escapeHtml(alert.base_name || "Unknown")}</strong>
                    </div>
                    <div class="muted">
                        Distance: <strong>${Math.round(alert.distance_meters)}m</strong> &middot;
                        Triggered: ${escapeHtml(formatTime(alert.created_at))}
                    </div>
                    <div>${escapeHtml(alert.message)}</div>
                </div>
                <button type="button" class="btn btn-secondary btn-sm ack-alert-btn" data-alert-id="${escapeHtml(alert.alert_id)}">
                    Acknowledge
                </button>
            </div>`
            )
            .join("");

        container.querySelectorAll(".ack-alert-btn").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const alertId = btn.getAttribute("data-alert-id");
                btn.disabled = true;
                try {
                    const resp = await fetch(`/api/alerts/${encodeURIComponent(alertId)}/acknowledge`, {
                        method: "POST",
                        credentials: "same-origin",
                        headers: {
                            "X-CSRF-Token": getCsrfToken(),
                        },
                    });
                    if (resp.ok) {
                        await refreshDashboard();
                    }
                } finally {
                    btn.disabled = false;
                }
            });
        });
    }

    function renderChildren(children) {
        const tbody = document.getElementById("children-tbody");
        const countEl = document.getElementById("children-count");
        if (countEl) {
            countEl.textContent = String(children.length);
        }
        if (!tbody) {
            return;
        }
        if (!children.length) {
            tbody.innerHTML = `<tr><td colspan="6" class="muted">No children added yet. <a href="/children/add">Add your first child</a>.</td></tr>`;
            return;
        }

        tbody.innerHTML = children
            .map((child) => {
                const coords =
                    child.latitude != null && child.longitude != null
                        ? `${Number(child.latitude).toFixed(5)}, ${Number(child.longitude).toFixed(5)}`
                        : "Not reported";
                const updated = child.location_updated_at
                    ? formatTime(child.location_updated_at)
                    : "Never";
                const baseDetails = (child.per_base || []).length
                    ? child.per_base
                          .map(
                              (b) =>
                                  `<div>${escapeHtml(b.base_name)}: ${Math.round(b.distance_meters)}m (<span class="badge badge-${escapeHtml(b.status)}">${escapeHtml(b.status)}</span>)</div>`
                          )
                          .join("")
                    : `<span class="muted">&mdash;</span>`;

                return `
                <tr>
                    <td><a href="/children/${encodeURIComponent(child.user_id)}"><strong>${escapeHtml(child.username)}</strong></a></td>
                    <td class="mono">${escapeHtml(coords)}</td>
                    <td>${escapeHtml(updated)}</td>
                    <td><span class="badge badge-${escapeHtml(child.monitoring_status)}">${escapeHtml(child.status_label)}</span></td>
                    <td>${baseDetails}</td>
                    <td><a href="/children/${encodeURIComponent(child.user_id)}" class="btn btn-secondary btn-sm">History</a></td>
                </tr>`;
            })
            .join("");
    }

    function renderDashboard(data) {
        const basesCountEl = document.getElementById("bases-count");
        if (basesCountEl) {
            basesCountEl.textContent = String((data.bases || []).length);
        }
        renderGuardianCard(data.guardian || {});
        renderAlerts(data.alerts || []);
        renderChildren(data.children || []);
        renderMapLayers(data);
    }

    async function refreshDashboard() {
        if (refreshing) {
            return;
        }
        refreshing = true;
        try {
            const resp = await fetch("/api/dashboard", { credentials: "same-origin" });
            if (resp.status === 401) {
                window.location.href = "/login";
                return;
            }
            if (!resp.ok) {
                return;
            }
            const data = await resp.json();
            renderDashboard(data);
        } finally {
            refreshing = false;
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        const initialEl = document.getElementById("initial-dashboard-data");
        if (!initialEl) {
            return;
        }
        const initialData = JSON.parse(initialEl.textContent || "{}");
        initMap(initialData);
        renderDashboard(initialData);

        window.addEventListener("scatela:location-updated", () => {
            refreshDashboard();
        });
        setInterval(refreshDashboard, 10000);
    });
})();
