from datetime import datetime, timedelta, timezone

from backend.database import db
from backend.models import Child, Child_Log, Guardian
from backend.services.exceptions import NotFoundError, ValidationError
from backend.services.monitoring_service import (
    evaluate_child_for_all_guardians,
    evaluate_guardian_children,
    get_stale_threshold_seconds,
    is_location_fresh,
    utcnow_naive,
)
from backend.services.user_service import get_user_and_role
from backend.services.validation import validate_coordinates


def parse_optional_timestamp(value) -> datetime | None:
    """Parse an ISO-8601 timestamp string or epoch milliseconds into naive UTC datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValidationError("Invalid timestamp format.")
    if isinstance(value, (int, float)):
        # Handle epoch seconds or epoch milliseconds
        seconds = float(value) / 1000.0 if value > 1e11 else float(value)
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(tzinfo=None)
        except (OverflowError, OSError, ValueError):
            raise ValidationError("Invalid timestamp value.")
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            raise ValidationError("Invalid ISO timestamp format.")
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    raise ValidationError("Invalid timestamp format.")


def update_user_location(
    user_id,
    latitude,
    longitude,
    client_timestamp=None,
) -> dict:
    """
    Update current coordinates for the authenticated guardian or child.
    Never inserts a duplicate guardian/child record; records child history in child_log,
    rejects stale/out-of-order timestamps, and invokes the monitoring service.
    """
    lat, lon = validate_coordinates(latitude, longitude)
    user, role = get_user_and_role(user_id)
    if user is None or role is None:
        raise NotFoundError("Authenticated user profile not found.")

    now = utcnow_naive()
    parsed_client_ts = parse_optional_timestamp(client_timestamp)
    stale_seconds = get_stale_threshold_seconds()

    if parsed_client_ts is not None:
        age = (now - parsed_client_ts).total_seconds()
        if age > stale_seconds:
            raise ValidationError("Stale location coordinates cannot be treated as current.")
        if age < -300:
            raise ValidationError("Location timestamp is too far in the future.")

    if role == "guardian":
        profile = Guardian.query.filter_by(user_id=user.user_id).first()
        if profile is None:
            raise NotFoundError("Guardian profile not found.")

        if (
            parsed_client_ts is not None
            and profile.location_updated_at is not None
            and parsed_client_ts < profile.location_updated_at - timedelta(seconds=5)
        ):
            raise ValidationError("Outdated location timestamp ignored.")

        profile.latitude = lat
        profile.longitude = lon
        profile.location_updated_at = now
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        monitoring = evaluate_guardian_children(user.user_id, now=now)
        return {
            "role": "guardian",
            "latitude": profile.latitude,
            "longitude": profile.longitude,
            "location_updated_at": profile.location_updated_at.isoformat(),
            "monitoring": monitoring,
        }

    profile = Child.query.filter_by(user_id=user.user_id).first()
    if profile is None:
        raise NotFoundError("Child profile not found.")

    if (
        parsed_client_ts is not None
        and profile.location_updated_at is not None
        and parsed_client_ts < profile.location_updated_at
    ):
        raise ValidationError("Outdated location timestamp ignored.")

    profile.latitude = lat
    profile.longitude = lon
    profile.location_updated_at = now

    log_entry = Child_Log(
        child_id=profile.user_id,
        latitude=lat,
        longitude=lon,
        created_at=now,
    )
    try:
        db.session.add(log_entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    monitoring = evaluate_child_for_all_guardians(user.user_id, now=now)
    return {
        "role": "child",
        "latitude": profile.latitude,
        "longitude": profile.longitude,
        "location_updated_at": profile.location_updated_at.isoformat(),
        "log_id": str(log_entry.log_id),
        "monitoring": monitoring,
    }


def get_user_location(user_id) -> dict:
    """Return latest stored coordinates and timestamp for the authenticated user."""
    user, role = get_user_and_role(user_id)
    if user is None or role is None:
        raise NotFoundError("Authenticated user profile not found.")

    profile = (
        Guardian.query.filter_by(user_id=user.user_id).first()
        if role == "guardian"
        else Child.query.filter_by(user_id=user.user_id).first()
    )
    if profile is None:
        raise NotFoundError("User location profile not found.")

    return {
        "role": role,
        "username": user.username,
        "latitude": profile.latitude,
        "longitude": profile.longitude,
        "location_updated_at": (
            profile.location_updated_at.isoformat() if profile.location_updated_at else None
        ),
        "location_fresh": is_location_fresh(
            profile.latitude,
            profile.longitude,
            profile.location_updated_at,
        ),
    }
