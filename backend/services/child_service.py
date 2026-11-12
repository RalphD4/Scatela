from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from backend.database import db
from backend.models import Child, Child_Log, Guardian, Users
from backend.services.exceptions import AuthorizationError, ConflictError, NotFoundError
from backend.services.monitoring_service import (
    STATUS_LABELS,
    get_guardian_dashboard_data,
    is_location_fresh,
)
from backend.services.validation import (
    parse_uuid,
    validate_email,
    validate_password,
    validate_phone_number,
    validate_username,
)


def create_child_for_guardian(
    guardian_id,
    username: str | None,
    email: str | None,
    phone_number: str | None,
    password: str | None,
    confirm_password: str | None = None,
) -> Child:
    """Create a child user account, child profile, and guardian_child link atomically."""
    gid = parse_uuid(guardian_id, "guardian ID")
    guardian = Guardian.query.filter_by(user_id=gid).first()
    if guardian is None:
        raise NotFoundError("Guardian account not found.")

    clean_username = validate_username(username)
    clean_email = validate_email(email)
    clean_phone = validate_phone_number(phone_number)
    clean_password = validate_password(password, confirm_password)

    if Users.query.filter_by(username=clean_username).first() is not None:
        raise ConflictError("Username is already in use.")
    if Users.query.filter_by(email=clean_email).first() is not None:
        raise ConflictError("Email is already registered.")

    user = Users(
        username=clean_username,
        password_hash=generate_password_hash(clean_password),
        email=clean_email,
        phone_number=clean_phone,
    )

    try:
        db.session.add(user)
        db.session.flush()

        child = Child(
            user_id=user.user_id,
            longitude=None,
            latitude=None,
            location_updated_at=None,
        )
        db.session.add(child)
        db.session.flush()

        if child not in guardian.children:
            guardian.children.append(child)

        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ConflictError("A user with that username or email already exists.")
    except Exception:
        db.session.rollback()
        raise

    return child


def verify_guardian_owns_child(guardian_id, child_id) -> Child:
    """Verify child exists and belongs to the authenticated guardian."""
    gid = parse_uuid(guardian_id, "guardian ID")
    cid = parse_uuid(child_id, "child ID")

    child = Child.query.filter_by(user_id=cid).first()
    if child is None:
        raise NotFoundError("Child account not found.")

    is_owned = any(g.user_id == gid for g in child.guardians)
    if not is_owned:
        raise AuthorizationError("You do not have permission to access this child.")

    return child


def get_guardian_children(guardian_id) -> list[dict]:
    """Return all children belonging to the authenticated guardian with monitoring status."""
    dashboard = get_guardian_dashboard_data(guardian_id)
    return dashboard.get("children", [])


def get_child_detail_for_guardian(guardian_id, child_id, log_limit: int = 50) -> dict:
    """Return child profile, monitoring status across bases, and recent location logs."""
    child = verify_guardian_owns_child(guardian_id, child_id)
    dashboard = get_guardian_dashboard_data(guardian_id)

    child_summary = next(
        (c for c in dashboard.get("children", []) if c["user_id"] == str(child.user_id)),
        {
            **child.to_dict(),
            "location_fresh": is_location_fresh(
                child.latitude, child.longitude, child.location_updated_at
            ),
            "monitoring_status": "no_location",
            "status_label": STATUS_LABELS["no_location"],
            "per_base": [],
        },
    )

    logs = (
        Child_Log.query.filter_by(child_id=child.user_id)
        .order_by(Child_Log.created_at.desc())
        .limit(log_limit)
        .all()
    )

    child_alerts = [
        alert for alert in dashboard.get("alerts", []) if alert["child_id"] == str(child.user_id)
    ]

    return {
        "child": child_summary,
        "bases": dashboard.get("bases", []),
        "logs": [entry.to_dict() for entry in logs],
        "alerts": child_alerts,
    }
