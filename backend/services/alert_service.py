from datetime import datetime, timezone

from backend.database import db
from backend.models import Alert, Child, ChildBaseStatus, Bases
from backend.services.exceptions import AuthorizationError, NotFoundError
from backend.services.validation import parse_uuid


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def handle_status_transition(
    guardian_id,
    child: Child,
    base: Bases,
    new_status: str,
    distance_meters: float,
    now: datetime | None = None,
) -> Alert | None:
    """
    Persist the latest (child, base) monitoring status and create an alert only
    when the child's monitoring state for that base changes into warning or danger.
    """
    timestamp = now or _utcnow_naive()
    existing_status = ChildBaseStatus.query.filter_by(
        child_id=child.user_id,
        base_id=base.base_id,
    ).first()

    prev_status = existing_status.status if existing_status is not None else None

    if existing_status is None:
        existing_status = ChildBaseStatus(
            child_id=child.user_id,
            base_id=base.base_id,
            status=new_status,
            distance_meters=distance_meters,
            updated_at=timestamp,
        )
        db.session.add(existing_status)
    else:
        existing_status.status = new_status
        existing_status.distance_meters = distance_meters
        existing_status.updated_at = timestamp

    if prev_status == new_status:
        return None

    # Resolve any prior active alerts for this child + base on state change
    active_alerts = Alert.query.filter_by(
        guardian_id=guardian_id,
        child_id=child.user_id,
        base_id=base.base_id,
        is_active=True,
    ).all()
    for prior in active_alerts:
        prior.is_active = False
        prior.resolved_at = timestamp

    if new_status not in ("warning", "danger"):
        return None

    child_name = child.user.username if child.user else "Child"
    severity_label = "Danger" if new_status == "danger" else "Warning"
    threshold = base.danger_radius if new_status == "danger" else base.warning_radius
    message = (
        f"{severity_label}: {child_name} is {distance_meters:.0f}m from "
        f"{base.base_name} (limit {threshold}m)."
    )

    alert = Alert(
        guardian_id=guardian_id,
        child_id=child.user_id,
        base_id=base.base_id,
        alert_type=new_status,
        distance_meters=distance_meters,
        message=message,
        is_active=True,
        created_at=timestamp,
    )
    db.session.add(alert)
    return alert


def list_guardian_alerts(guardian_id, active_only: bool = True, limit: int = 50) -> list[Alert]:
    """Return alerts belonging to the specified guardian ordered newest first."""
    gid = parse_uuid(guardian_id, "guardian ID")
    query = Alert.query.filter_by(guardian_id=gid)
    if active_only:
        query = query.filter_by(is_active=True)
    return query.order_by(Alert.created_at.desc()).limit(limit).all()


def acknowledge_alert(guardian_id, alert_id) -> Alert:
    """Resolve/acknowledge an alert after verifying guardian ownership."""
    gid = parse_uuid(guardian_id, "guardian ID")
    aid = parse_uuid(alert_id, "alert ID")

    alert = Alert.query.filter_by(alert_id=aid).first()
    if alert is None:
        raise NotFoundError("Alert not found.")
    if alert.guardian_id != gid:
        raise AuthorizationError("You do not have permission to modify this alert.")

    if alert.is_active:
        alert.is_active = False
        alert.resolved_at = _utcnow_naive()
        db.session.commit()

    return alert
