import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict

from backend.services.exceptions import ServiceError, ValidationError

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "Scatela-Child-Safety-Monitor/1.0 (https://github.com/RalphD4/Scatela)"
_MIN_REQUEST_INTERVAL_SECONDS = 1.05
_CACHE_TTL_SECONDS = 3600
_MAX_CACHE_SIZE = 100

_rate_lock = threading.Lock()
_last_request_time = 0.0
_cache: OrderedDict[str, tuple[float, list[dict]]] = OrderedDict()


def search_places(query: str | None, limit: int = 5) -> list[dict]:
    """
    Search places via OpenStreetMap Nominatim while adhering to Nominatim's
    usage policy (valid User-Agent, <= 1 req/sec rate limiting, caching).
    """
    global _last_request_time

    if not isinstance(query, str) or len(query.strip()) < 2:
        raise ValidationError("Please enter at least 2 characters to search for an address or place.")

    cleaned = query.strip()
    cache_key = cleaned.lower()
    now = time.monotonic()

    with _rate_lock:
        cached = _cache.get(cache_key)
        if cached is not None:
            cached_at, results = cached
            if now - cached_at < _CACHE_TTL_SECONDS:
                _cache.move_to_end(cache_key)
                return results
            del _cache[cache_key]

        elapsed = now - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL_SECONDS:
            time.sleep(_MIN_REQUEST_INTERVAL_SECONDS - elapsed)

        params = urllib.parse.urlencode(
            {
                "q": cleaned,
                "format": "jsonv2",
                "limit": max(1, min(int(limit), 8)),
                "addressdetails": 1,
            }
        )
        req = urllib.request.Request(
            f"{_NOMINATIM_URL}?{params}",
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                raw_payload = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError):
            _last_request_time = time.monotonic()
            raise ServiceError(
                "Address lookup service is temporarily unavailable. You can still click the map or enter coordinates directly.",
                status_code=503,
            )

        _last_request_time = time.monotonic()

        try:
            parsed = json.loads(raw_payload)
        except ValueError:
            raise ServiceError("Invalid response received from address lookup service.", status_code=502)

        results = []
        for item in parsed:
            try:
                lat = float(item["lat"])
                lon = float(item["lon"])
            except (KeyError, TypeError, ValueError):
                continue
            results.append(
                {
                    "display_name": item.get("display_name", f"{lat:.5f}, {lon:.5f}"),
                    "latitude": lat,
                    "longitude": lon,
                }
            )

        _cache[cache_key] = (_last_request_time, results)
        if len(_cache) > _MAX_CACHE_SIZE:
            _cache.popitem(last=False)

        return results
