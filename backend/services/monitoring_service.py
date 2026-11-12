import os
from datetime import datetime, timezone

from flask import current_app, has_app_context

from backend.database import db
from backend.models import Bases, Child, Guardian
from backend.services.alert_service import handle_status_transition, list_guardian_alerts
from backend.services.distance_service import (
    evaluate_threshold,
    haversine_distance_meters,
    highest_severity,
)
from backend.services.validation import parse_uuid

DEFAULT_STALE_SECONDS = 300

STATUS_LABELS = {
    "normal": "Normal",
    "warning": "Warning",
    "danger": "Danger",
    "stale": "Stale Location",
    "no_location": "Awaiting Location",
    "no_bases": "No Bases Configured",
}


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_stale_threshold_seconds() -> int:
    """Return the maximum age in seconds before coordinates are treated as stale."""
    if has_app_context():
        configured = current_app.config.get("LOCATION_STALE_SECONDS")
        if configured is not None:
            return int(configured)
    return int(os.getenv("LOCATION_STALE_SECONDS", str(DEFAULT_STALE_SECONDS)))


def is_location_fresh(
    latitude: float | None,
    longitude: float | None,
    location_updated_at: datetime | None,
    now: datetime | None = None,
    stale_seconds: int | None = None,
) -> bool:
    """Check whether coordinates exist and their timestamp is within the freshness window."""
    if latitude is None or longitude is None or location_updated_at is None:
        return False

    ref_now = now or utcnow_naive()
    max_age = stale_seconds if stale_seconds is not None else get_stale_threshold_seconds()
    age_seconds = (ref_now - location_updated_at).total_seconds()
    return -60 <= age_seconds <= max_age


def _build_per_base_snapshot(
    child: Child,
    bases: list[Bases],
    now: datetime,
    evaluate_and_alert: bool,
    guardian_id,
) -> tuple[str, list[dict], list[dict]]:
    """Evaluate a child against every guardian base and return (overall_status, base_results, new_alerts)."""
    if not bases:
        return "no_bases", [], []

    if child.latitude is None or child.longitude is None:
        return "no_location", [], []

    if not is_location_fresh(child.latitude, child.longitude, child.location_updated_at, now=now):
        return "stale", [], []

    evaluations: list[dict] = []
    statuses: list[str] = []
    emitted_alerts: list[dict] = []

    for base in bases:
        if base.latitude is None or base.longitude is None:
            continue
        distance = haversine_distance_meters(
            child.latitude,
            child.longitude,
            base.latitude,
            base.longitude,
        )
        status = evaluate_threshold(distance, base.warning_radius, base.danger_radius)
        statuses.append(status)
        evaluations.append(
            {
                "base_id": str(base.base_id),
                "base_name": base.base_name,
                "distance_meters": round(distance, 2),
                "warning_radius": base.warning_radius,
                "danger_radius": base.danger_radius,
                "status": status,
                "status_label": STATUS_LABELS[status],
            }
        )

        if evaluate_and_alert:
            alert = handle_status_transition(
                guardian_id=guardian_id,
                child=child,
                base=base,
                new_status=status,
                distance_meters=distance,
                now=now,
            )
            if alert is not None:
                emitted_alerts.append(alert.to_dict())

    overall = highest_severity(statuses)
    return overall, evaluations, emitted_alerts


def evaluate_guardian_children(guardian_id, now: datetime | None = None) -> dict:
    """
    Run full monitoring workflow for all children belonging to a guardian:
    1. Retrieve latest guardian coordinates & timestamp
    2. Retrieve each child's latest coordinates & timestamp
    3. Retrieve all guardian bases
    4. Compute distances, classify thresholds, and emit alerts on state transitions.
    """
    gid = parse_uuid(guardian_id, "guardian ID")
    guardian = Guardian.query.filter_by(user_id=gid).first()
    if guardian is None:
        return {"evaluated_children": [], "new_alerts": []}

    ref_now = now or utcnow_naive()
    bases = Bases.query.filter_by(user_id=gid).order_by(Bases.created_at.asc()).all()
    guardian_fresh = is_location_fresh(
        guardian.latitude,
        guardian.longitude,
        guardian.location_updated_at,
        now=ref_now,
    )

    evaluated_children = []
    all_new_alerts = []

    for child in guardian.children:
        overall, per_base, new_alerts = _build_per_base_snapshot(
            child=child,
            bases=bases,
            now=ref_now,
            evaluate_and_alert=True,
            guardian_id=gid,
        )
        all_new_alerts.extend(new_alerts)
        evaluated_children.append(
            {
                "child_id": str(child.user_id),
                "username": child.user.username if child.user else None,
                "monitoring_status": overall,
                "status_label": STATUS_LABELS[overall],
                "bases": per_base,
            }
        )

    db.session.commit()
    return {
        "guardian_location_fresh": guardian_fresh,
        "evaluated_children": evaluated_children,
        "new_alerts": all_new_alerts,
    }


def evaluate_child_for_all_guardians(child_id, now: datetime | None = None) -> dict:
    """Evaluate a child against all bases of every guardian associated with that child."""
    cid = parse_uuid(child_id, "child ID")
    child = Child.query.filter_by(user_id=cid).first()
    if child is None:
        return {"guardians_evaluated": 0, "new_alerts": []}

    ref_now = now or utcnow_naive()
    new_alerts = []
    highest_statuses = []

    for guardian in child.guardians:
        bases = Bases.query.filter_by(user_id=guardian.user_id).order_by(Bases.created_at.asc()).all()
        overall, _, emitted = _build_per_base_snapshot(
            child=child,
            bases=bases,
            now=ref_now,
            evaluate_and_alert=True,
            guardian_id=guardian.user_id,
        )
        new_alerts.extend(emitted)
        if overall in ("normal", "warning", "danger"):
            highest_statuses.append(overall)

    db.session.commit()
    overall_status = highest_severity(highest_statuses) if highest_statuses else None
    return {
        "guardians_evaluated": len(child.guardians),
        "monitoring_status": overall_status,
        "new_alerts": new_alerts,
    }


def get_guardian_dashboard_data(guardian_id) -> dict:
    """Build complete, read-only dashboard data for the authenticated guardian."""
    gid = parse_uuid(guardian_id, "guardian ID")
    guardian = Guardian.query.filter_by(user_id=gid).first()
    if guardian is None:
        return {}

    ref_now = utcnow_naive()
    bases = Bases.query.filter_by(user_id=gid).order_by(Bases.created_at.asc()).all()

    guardian_fresh = is_location_fresh(
        guardian.latitude,
        guardian.longitude,
        guardian.location_updated_at,
        now=ref_now,
    )

    children_data = []
    for child in sorted(
        guardian.children,
        key=lambda c: (c.user.username.lower() if c.user and c.user.username else ""),
    ):
        child_fresh = is_location_fresh(
            child.latitude,
            child.longitude,
            child.location_updated_at,
            now=ref_now,
        )
        overall, per_base, _ = _build_per_base_snapshot(
            child=child,
            bases=bases,
            now=ref_now,
            evaluate_and_alert=False,
            guardian_id=gid,
        )
        children_data.append(
            {
                "user_id": str(child.user_id),
                "username": child.user.username if child.user else None,
                "email": child.user.email if child.user else None,
                "phone_number": child.user.phone_number if child.user else None,
                "latitude": child.latitude,
                "longitude": child.longitude,
                "location_updated_at": (
                    child.location_updated_at.isoformat() if child.location_updated_at else None
                ),
                "location_fresh": child_fresh,
                "monitoring_status": overall,
                "status_label": STATUS_LABELS[overall],
                "per_base": per_base,
            }
        )

    active_alerts = [alert.to_dict() for alert in list_guardian_alerts(gid, active_only=True)]

    return {
        "guardian": {
            **guardian.to_dict(),
            "location_fresh": guardian_fresh,
        },
        "bases": [base.to_dict() for base in bases],
        "children": children_data,
        "alerts": active_alerts,
        "stale_threshold_seconds": get_stale_threshold_seconds(),
    }
