from flask import Blueprint, g, render_template

from backend.models import Child
from backend.services.auth_service import child_required
from backend.services.monitoring_service import is_location_fresh

child_web = Blueprint("child_web", __name__)


@child_web.route("/child")
@child_required
def tracker():
    child = Child.query.filter_by(user_id=g.current_user.user_id).first()
    guardian_names = [
        guardian.user.username
        for guardian in (child.guardians if child else [])
        if guardian.user is not None
    ]
    child_data = child.to_dict() if child else {}
    child_data["location_fresh"] = (
        is_location_fresh(child.latitude, child.longitude, child.location_updated_at)
        if child
        else False
    )
    return render_template(
        "child_tracker.html",
        child=child_data,
        guardian_names=guardian_names,
    )
