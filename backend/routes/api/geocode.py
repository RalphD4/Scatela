from flask import Blueprint, jsonify, request

from backend.services.auth_service import login_required
from backend.services.geocode_service import search_places

geocode_api = Blueprint("geocode_api", __name__, url_prefix="/api")


@geocode_api.route("/geocode", methods=["GET"])
@login_required
def geocode_search():
    query = request.args.get("q", "")
    results = search_places(query)
    return jsonify({"results": results}), 200
