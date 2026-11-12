from flask import Blueprint, g, jsonify, request

from backend.services.alert_service import acknowledge_alert, list_guardian_alerts
from backend.services.auth_service import guardian_required
from backend.services.base_service import (
    create_base,
    delete_base,
    get_guardian_base,
    list_guardian_bases,
    update_base,
)
from backend.services.child_service import (
    create_child_for_guardian,
    get_child_detail_for_guardian,
    get_guardian_children,
)
from backend.services.exceptions import ValidationError
from backend.services.monitoring_service import get_guardian_dashboard_data

guardian_api = Blueprint("guardian_api", __name__, url_prefix="/api")


@guardian_api.route("/dashboard", methods=["GET"])
@guardian_required
def api_dashboard():
    return jsonify(get_guardian_dashboard_data(g.current_user.user_id)), 200


@guardian_api.route("/children", methods=["GET", "POST"])
@guardian_required
def api_children():
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValidationError("Request body must be valid JSON.")
        child = create_child_for_guardian(
            guardian_id=g.current_user.user_id,
            username=data.get("username"),
            email=data.get("email"),
            phone_number=data.get("phone_number"),
            password=data.get("password"),
            confirm_password=data.get("confirm_password"),
        )
        return jsonify({"child": child.to_dict()}), 201

    return jsonify({"children": get_guardian_children(g.current_user.user_id)}), 200


@guardian_api.route("/children/<child_id>/logs", methods=["GET"])
@guardian_required
def api_child_logs(child_id):
    limit = request.args.get("limit", 50, type=int) or 50
    limit = max(1, min(limit, 200))
    detail = get_child_detail_for_guardian(g.current_user.user_id, child_id, log_limit=limit)
    return jsonify(detail), 200


@guardian_api.route("/bases", methods=["GET", "POST"])
@guardian_required
def api_bases():
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValidationError("Request body must be valid JSON.")
        base = create_base(
            guardian_id=g.current_user.user_id,
            base_name=data.get("base_name"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            warning_radius=data.get("warning_radius"),
            danger_radius=data.get("danger_radius"),
        )
        return jsonify({"base": base.to_dict()}), 201

    bases = [base.to_dict() for base in list_guardian_bases(g.current_user.user_id)]
    return jsonify({"bases": bases}), 200


@guardian_api.route("/bases/<base_id>", methods=["GET", "PUT", "DELETE"])
@guardian_required
def api_base_detail(base_id):
    if request.method == "GET":
        base = get_guardian_base(g.current_user.user_id, base_id)
        return jsonify({"base": base.to_dict()}), 200

    if request.method == "PUT":
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValidationError("Request body must be valid JSON.")
        base = update_base(
            guardian_id=g.current_user.user_id,
            base_id=base_id,
            base_name=data.get("base_name"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            warning_radius=data.get("warning_radius"),
            danger_radius=data.get("danger_radius"),
        )
        return jsonify({"base": base.to_dict()}), 200

    delete_base(g.current_user.user_id, base_id)
    return jsonify({"deleted": True}), 200


@guardian_api.route("/alerts", methods=["GET"])
@guardian_required
def api_alerts():
    active_only = request.args.get("active_only", "true").lower() != "false"
    alerts = [a.to_dict() for a in list_guardian_alerts(g.current_user.user_id, active_only=active_only)]
    return jsonify({"alerts": alerts}), 200


@guardian_api.route("/alerts/<alert_id>/acknowledge", methods=["POST"])
@guardian_required
def api_acknowledge_alert(alert_id):
    alert = acknowledge_alert(g.current_user.user_id, alert_id)
    return jsonify({"alert": alert.to_dict()}), 200
