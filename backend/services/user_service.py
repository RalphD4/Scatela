from sqlalchemy import or_

from backend.models import Child, Guardian, Users
from backend.services.validation import parse_uuid


def get_user_by_id(user_id) -> Users | None:
    """Fetch a user record by UUID string or UUID instance."""
    try:
        uid = parse_uuid(user_id, "user ID")
    except Exception:
        return None
    return Users.query.filter_by(user_id=uid).first()


def get_user_by_identifier(identifier: str | None) -> Users | None:
    """Fetch a user by username or case-insensitive email."""
    if not isinstance(identifier, str):
        return None
    cleaned = identifier.strip()
    if not cleaned:
        return None
    return Users.query.filter(
        or_(Users.username == cleaned, Users.email == cleaned.lower())
    ).first()


def get_user_role(user_id) -> str | None:
    """Determine role ('guardian' or 'child') from database profile tables."""
    try:
        uid = parse_uuid(user_id, "user ID")
    except Exception:
        return None

    if Guardian.query.filter_by(user_id=uid).first() is not None:
        return "guardian"
    if Child.query.filter_by(user_id=uid).first() is not None:
        return "child"
    return None


def get_user_and_role(user_id) -> tuple[Users | None, str | None]:
    """Return the Users record and database-backed role for a user ID."""
    user = get_user_by_id(user_id)
    if user is None:
        return None, None
    role = get_user_role(user.user_id)
    if role is None:
        return None, None
    return user, role
