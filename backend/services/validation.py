import math
import re
import uuid

from backend.services.exceptions import ValidationError

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,20}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^[0-9+\-()\s]{7,20}$")


def validate_username(username: str | None) -> str:
    if not isinstance(username, str):
        raise ValidationError("Username is required.")
    cleaned = username.strip()
    if not _USERNAME_RE.match(cleaned):
        raise ValidationError(
            "Username must be 3 to 20 characters using letters, numbers, '.', '-', or '_'."
        )
    return cleaned


def validate_email(email: str | None) -> str:
    if not isinstance(email, str):
        raise ValidationError("Email is required.")
    cleaned = email.strip().lower()
    if len(cleaned) > 254 or not _EMAIL_RE.match(cleaned):
        raise ValidationError("Please provide a valid email address.")
    return cleaned


def validate_phone_number(phone_number: str | None) -> str:
    if not isinstance(phone_number, str):
        raise ValidationError("Phone number is required.")
    cleaned = phone_number.strip()
    digits = sum(ch.isdigit() for ch in cleaned)
    if not _PHONE_RE.match(cleaned) or digits < 7:
        raise ValidationError("Please provide a valid phone number (7 to 20 characters).")
    return cleaned


def validate_password(password: str | None, confirm_password: str | None = None) -> str:
    if not isinstance(password, str) or len(password) < 6:
        raise ValidationError("Password must be at least 6 characters long.")
    if len(password) > 128:
        raise ValidationError("Password must not exceed 128 characters.")
    if confirm_password is not None and password != confirm_password:
        raise ValidationError("Passwords do not match.")
    return password


def parse_uuid(value, field_name: str = "ID") -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    if not isinstance(value, str):
        raise ValidationError(f"Invalid {field_name}.")
    try:
        return uuid.UUID(value.strip())
    except (ValueError, AttributeError):
        raise ValidationError(f"Invalid {field_name}.")


def validate_coordinates(latitude, longitude) -> tuple[float, float]:
    if latitude is None or longitude is None:
        raise ValidationError("Latitude and longitude are required.")
    if isinstance(latitude, bool) or isinstance(longitude, bool):
        raise ValidationError("Latitude and longitude must be valid numbers.")
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        raise ValidationError("Latitude and longitude must be valid numbers.")

    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise ValidationError("Latitude and longitude must be finite numbers.")
    if not (-90.0 <= lat <= 90.0):
        raise ValidationError("Latitude must be between -90 and 90.")
    if not (-180.0 <= lon <= 180.0):
        raise ValidationError("Longitude must be between -180 and 180.")
    return lat, lon
