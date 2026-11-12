from backend.database import db
from backend.models import Bases, Guardian
from backend.services.exceptions import AuthorizationError, NotFoundError, ValidationError
from backend.services.monitoring_service import evaluate_guardian_children
from backend.services.validation import parse_uuid, validate_coordinates


def validate_base_payload(
    base_name: str | None,
    latitude,
    longitude,
    warning_radius,
    danger_radius,
) -> tuple[str, float, float, int, int]:
    """Validate base location input fields and threshold radii."""
    if not isinstance(base_name, str) or not base_name.strip():
        raise ValidationError("Base name is required.")
    clean_name = base_name.strip()
    if len(clean_name) > 100:
        raise ValidationError("Base name must be 100 characters or fewer.")

    lat, lon = validate_coordinates(latitude, longitude)

    if isinstance(warning_radius, bool) or isinstance(danger_radius, bool):
        raise ValidationError("Warning and danger radii must be positive whole numbers.")
    try:
        warn_r = int(float(warning_radius))
        danger_r = int(float(danger_radius))
    except (TypeError, ValueError):
        raise ValidationError("Warning and danger radii must be whole numbers in meters.")

    if str(warning_radius).strip() == "" or str(danger_radius).strip() == "":
        raise ValidationError("Warning and danger radii are required.")

    if warn_r <= 0:
        raise ValidationError("Warning radius must be greater than 0 meters.")
    if danger_r <= warn_r:
        raise ValidationError("Danger radius must be strictly greater than warning radius.")
    if danger_r > 1_000_000:
        raise ValidationError("Danger radius cannot exceed 1,000,000 meters.")

    return clean_name, lat, lon, warn_r, danger_r


def create_base(
    guardian_id,
    base_name: str | None,
    latitude,
    longitude,
    warning_radius,
    danger_radius,
) -> Bases:
    """Create a base location for the guardian and re-evaluate children."""
    gid = parse_uuid(guardian_id, "guardian ID")
    guardian = Guardian.query.filter_by(user_id=gid).first()
    if guardian is None:
        raise NotFoundError("Guardian account not found.")

    clean_name, lat, lon, warn_r, danger_r = validate_base_payload(
        base_name, latitude, longitude, warning_radius, danger_radius
    )

    base = Bases(
        user_id=gid,
        base_name=clean_name,
        latitude=lat,
        longitude=lon,
        warning_radius=warn_r,
        danger_radius=danger_r,
    )
    try:
        db.session.add(base)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    evaluate_guardian_children(gid)
    return base


def list_guardian_bases(guardian_id) -> list[Bases]:
    """Return all base locations belonging to the specified guardian."""
    gid = parse_uuid(guardian_id, "guardian ID")
    return Bases.query.filter_by(user_id=gid).order_by(Bases.created_at.asc()).all()


def get_guardian_base(guardian_id, base_id) -> Bases:
    """Fetch a base and enforce guardian ownership."""
    gid = parse_uuid(guardian_id, "guardian ID")
    bid = parse_uuid(base_id, "base ID")

    base = Bases.query.filter_by(base_id=bid).first()
    if base is None:
        raise NotFoundError("Base location not found.")
    if base.user_id != gid:
        raise AuthorizationError("You do not have permission to access this base location.")
    return base


def update_base(
    guardian_id,
    base_id,
    base_name: str | None,
    latitude,
    longitude,
    warning_radius,
    danger_radius,
) -> Bases:
    """Update an existing base after enforcing ownership and re-evaluate children."""
    base = get_guardian_base(guardian_id, base_id)
    clean_name, lat, lon, warn_r, danger_r = validate_base_payload(
        base_name, latitude, longitude, warning_radius, danger_radius
    )

    base.base_name = clean_name
    base.latitude = lat
    base.longitude = lon
    base.warning_radius = warn_r
    base.danger_radius = danger_r

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    evaluate_guardian_children(base.user_id)
    return base


def delete_base(guardian_id, base_id) -> None:
    """Delete a base location after enforcing ownership."""
    base = get_guardian_base(guardian_id, base_id)
    try:
        db.session.delete(base)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
