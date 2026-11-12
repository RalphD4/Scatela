import math

EARTH_RADIUS_METERS = 6_371_000.0
SEVERITY_RANK = {
    "normal": 1,
    "warning": 2,
    "danger": 3,
}


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance in meters between two WGS84 coordinates."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_METERS * c


def evaluate_threshold(distance_meters: float, warning_radius: int, danger_radius: int) -> str:
    """Classify distance against warning and danger radii into normal/warning/danger."""
    if distance_meters <= warning_radius:
        return "normal"
    if distance_meters <= danger_radius:
        return "warning"
    return "danger"


def highest_severity(statuses: list[str]) -> str:
    """Return the highest-severity monitoring status among evaluated base statuses."""
    if not statuses:
        return "no_bases"
    return max(statuses, key=lambda status: SEVERITY_RANK.get(status, 0))
