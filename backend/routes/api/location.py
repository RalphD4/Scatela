from flask import Blueprint, g, jsonify, request

from backend.services.auth_service import login_required
from backend.services.exceptions import ValidationError
from backend.services.location_service import get_user_location, update_user_location

location_api = Blueprint("location_api", __name__, url_prefix="/api")


@location_api.route("/location", methods=["POST", "GET"])
@login_required
def location_endpoint():
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValidationError("Request body must be valid JSON.")

        result = update_user_location(
            user_id=g.current_user.user_id,
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            client_timestamp=data.get("timestamp"),
        )
        return jsonify(result), 200

    current_location = get_user_location(g.current_user.user_id)
    return jsonify(current_location), 200
