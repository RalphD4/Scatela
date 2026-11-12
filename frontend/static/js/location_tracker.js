(function () {
    const INTERVAL_MS = 10000;
    let intervalId = null;
    let inFlight = false;
    let stopped = false;

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") : "";
    }

    function setTrackingBar(message, stateClass) {
        const bar = document.getElementById("tracking-bar");
        const statusEl = document.getElementById("tracking-status-text");
        if (statusEl) {
            statusEl.textContent = message;
        }
        if (bar) {
            bar.classList.remove("error", "warning");
            if (stateClass) {
                bar.classList.add(stateClass);
            }
        }
    }

    function setMetaText(text) {
        const metaEl = document.getElementById("tracking-meta-text");
        if (metaEl) {
            metaEl.textContent = text;
        }
    }

    function formatLocalTime(isoString) {
        if (!isoString) {
            return "—";
        }
        const normalized = isoString.endsWith("Z") ? isoString : `${isoString}Z`;
        const parsed = new Date(normalized);
        if (Number.isNaN(parsed.getTime())) {
            return isoString;
        }
        return parsed.toLocaleString();
    }

    async function sendCoordinates(position) {
        if (stopped) {
            return;
        }
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;
        const timestamp = position.timestamp
            ? new Date(position.timestamp).toISOString()
            : new Date().toISOString();

        const response = await fetch("/api/location", {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRF-Token": getCsrfToken(),
            },
            body: JSON.stringify({ latitude, longitude, timestamp }),
        });

        if (response.status === 401) {
            stop();
            window.location.href = "/login";
            return;
        }

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || "Failed to update location.");
        }

        setTrackingBar("Automatic location tracking active (every 10s)", "");
        setMetaText(
            `Lat ${Number(data.latitude).toFixed(5)}, Lon ${Number(data.longitude).toFixed(5)} · Updated ${formatLocalTime(data.location_updated_at)}`
        );

        const retryBtn = document.getElementById("retry-location-btn");
        if (retryBtn) {
            retryBtn.hidden = true;
        }

        window.dispatchEvent(new CustomEvent("scatela:location-updated", { detail: data }));
    }

    function requestLocationOnce() {
        if (stopped || inFlight) {
            return;
        }

        if (!("geolocation" in navigator)) {
            setTrackingBar("Browser geolocation is not supported on this device.", "error");
            stop();
            return;
        }

        inFlight = true;
        navigator.geolocation.getCurrentPosition(
            async (position) => {
                try {
                    await sendCoordinates(position);
                } catch (err) {
                    setTrackingBar(`Location sync issue: ${err.message}`, "warning");
                } finally {
                    inFlight = false;
                }
            },
            (geoError) => {
                inFlight = false;
                if (stopped) {
                    return;
                }
                if (geoError.code === geoError.PERMISSION_DENIED) {
                    setTrackingBar(
                        "Location permission denied. Enable location access in your browser to resume tracking.",
                        "error"
                    );
                    const retryBtn = document.getElementById("retry-location-btn");
                    if (retryBtn) {
                        retryBtn.hidden = false;
                    }
                    stopIntervalOnly();
                } else if (geoError.code === geoError.TIMEOUT) {
                    setTrackingBar(
                        "Location request timed out. Retrying automatically in 10s...",
                        "warning"
                    );
                } else {
                    setTrackingBar(
                        "Unable to determine device location. Retrying automatically in 10s...",
                        "warning"
                    );
                }
            },
            {
                enableHighAccuracy: true,
                timeout: 8000,
                maximumAge: 0,
            }
        );
    }

    function stopIntervalOnly() {
        if (intervalId !== null) {
            clearInterval(intervalId);
            intervalId = null;
        }
    }

    function stop() {
        stopped = true;
        inFlight = false;
        stopIntervalOnly();
    }

    function start() {
        if (intervalId !== null) {
            return;
        }
        stopped = false;
        setTrackingBar("Requesting location permission...", "");
        requestLocationOnce();
        intervalId = setInterval(requestLocationOnce, INTERVAL_MS);
    }

    window.ScatelaTracker = {
        start,
        stop,
        formatLocalTime,
    };

    document.addEventListener("DOMContentLoaded", () => {
        const trackingBar = document.getElementById("tracking-bar");
        if (!trackingBar) {
            return;
        }

        const logoutForm = document.getElementById("logout-form");
        if (logoutForm) {
            logoutForm.addEventListener("submit", () => {
                stop();
                setTrackingBar("Stopping tracking and logging out...", "");
            });
        }

        const retryBtn = document.getElementById("retry-location-btn");
        if (retryBtn) {
            retryBtn.addEventListener("click", () => {
                retryBtn.hidden = true;
                start();
            });
        }

        window.addEventListener("pagehide", stop);
        start();
    });
})();
