(function () {
    document.addEventListener("DOMContentLoaded", () => {
        const mapEl = document.getElementById("base-picker-map");
        if (!mapEl || typeof L === "undefined") {
            return;
        }

        const latInput = document.getElementById("latitude");
        const lonInput = document.getElementById("longitude");
        const warnInput = document.getElementById("warning_radius");
        const dangerInput = document.getElementById("danger_radius");
        const searchInput = document.getElementById("address-search-input");
        const searchBtn = document.getElementById("address-search-btn");
        const searchStatus = document.getElementById("address-search-status");
        const resultsList = document.getElementById("address-search-results");
        const form = document.getElementById("base-location-form");

        const parsedLat = parseFloat(latInput.value);
        const parsedLon = parseFloat(lonInput.value);
        const defaultLat = parseFloat(mapEl.dataset.defaultLat);
        const defaultLon = parseFloat(mapEl.dataset.defaultLon);
        const initialLat = Number.isFinite(parsedLat) ? parsedLat : (Number.isFinite(defaultLat) ? defaultLat : 37.3382);
        const initialLon = Number.isFinite(parsedLon) ? parsedLon : (Number.isFinite(defaultLon) ? defaultLon : -121.8863);

        const map = L.map("base-picker-map").setView([initialLat, initialLon], 14);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(map);

        const marker = L.marker([initialLat, initialLon], { draggable: true }).addTo(map);
        const dangerCircle = L.circle([initialLat, initialLon], {
            radius: Math.max(1, parseInt(dangerInput.value, 10) || 500),
            color: "#dc2626",
            fillColor: "#ef4444",
            fillOpacity: 0.1,
            weight: 1.5,
        }).addTo(map);
        const warningCircle = L.circle([initialLat, initialLon], {
            radius: Math.max(1, parseInt(warnInput.value, 10) || 200),
            color: "#d97706",
            fillColor: "#f59e0b",
            fillOpacity: 0.16,
            weight: 1.5,
        }).addTo(map);

        function syncCircles() {
            const warnVal = parseInt(warnInput.value, 10);
            const dangerVal = parseInt(dangerInput.value, 10);
            if (!Number.isNaN(warnVal) && warnVal > 0) {
                warningCircle.setRadius(warnVal);
            }
            if (!Number.isNaN(dangerVal) && dangerVal > 0) {
                dangerCircle.setRadius(dangerVal);
            }
        }

        function setLocation(lat, lon, panMap) {
            const latLng = L.latLng(lat, lon);
            marker.setLatLng(latLng);
            warningCircle.setLatLng(latLng);
            dangerCircle.setLatLng(latLng);
            latInput.value = lat.toFixed(6);
            lonInput.value = lon.toFixed(6);
            if (panMap) {
                map.setView(latLng, Math.max(map.getZoom(), 15));
            }
        }

        marker.on("dragend", () => {
            const pos = marker.getLatLng();
            setLocation(pos.lat, pos.lng, false);
        });

        map.on("click", (event) => {
            setLocation(event.latlng.lat, event.latlng.lng, false);
        });

        function handleCoordinateInput() {
            const lat = parseFloat(latInput.value);
            const lon = parseFloat(lonInput.value);
            if (!Number.isNaN(lat) && !Number.isNaN(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
                const latLng = L.latLng(lat, lon);
                marker.setLatLng(latLng);
                warningCircle.setLatLng(latLng);
                dangerCircle.setLatLng(latLng);
                map.panTo(latLng);
            }
        }

        latInput.addEventListener("change", handleCoordinateInput);
        lonInput.addEventListener("change", handleCoordinateInput);
        warnInput.addEventListener("input", syncCircles);
        dangerInput.addEventListener("input", syncCircles);

        async function runAddressSearch() {
            const query = (searchInput.value || "").trim();
            resultsList.innerHTML = "";
            resultsList.hidden = true;

            if (query.length < 2) {
                searchStatus.textContent = "Enter at least 2 characters to search an address or place.";
                return;
            }

            searchBtn.disabled = true;
            searchStatus.textContent = "Searching OpenStreetMap Nominatim...";
            try {
                const resp = await fetch(`/api/geocode?q=${encodeURIComponent(query)}`, {
                    credentials: "same-origin",
                });
                const payload = await resp.json().catch(() => ({}));
                if (!resp.ok) {
                    searchStatus.textContent = payload.error || "Address search failed.";
                    return;
                }

                const items = payload.results || [];
                if (!items.length) {
                    searchStatus.textContent = "No matching places found. Try clicking the map directly.";
                    return;
                }

                searchStatus.textContent = "Select a result below, then drag the marker to fine-tune:";
                resultsList.hidden = false;
                items.forEach((item) => {
                    const li = document.createElement("li");
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.textContent = item.display_name;
                    btn.addEventListener("click", () => {
                        setLocation(item.latitude, item.longitude, true);
                        resultsList.hidden = true;
                        searchStatus.textContent = "Location selected. You can drag the marker to adjust.";
                    });
                    li.appendChild(btn);
                    resultsList.appendChild(li);
                });
            } catch (_err) {
                searchStatus.textContent =
                    "Address lookup failed. You can still click the map or enter coordinates manually.";
            } finally {
                searchBtn.disabled = false;
            }
        }

        if (searchBtn && searchInput) {
            searchBtn.addEventListener("click", runAddressSearch);
            searchInput.addEventListener("keydown", (event) => {
                if (event.key === "Enter") {
                    event.preventDefault();
                    runAddressSearch();
                }
            });
        }

        if (form) {
            form.addEventListener("submit", (event) => {
                const warnVal = parseInt(warnInput.value, 10);
                const dangerVal = parseInt(dangerInput.value, 10);
                if (Number.isNaN(warnVal) || warnVal <= 0 || Number.isNaN(dangerVal) || dangerVal <= warnVal) {
                    event.preventDefault();
                    alert("Danger radius must be strictly greater than warning radius (both > 0 meters).");
                }
            });
        }
    });
})();
