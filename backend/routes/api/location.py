from flask import Blueprint, request, jsonify, render_template

#route for location
#this should receive your current location and return it
location_api = Blueprint("location_api", __name__, url_prefix="/api") 




@location_api.route("/location", methods=["POST", "GET"])
def get_location():

    if request.method == "POST":
        #get the data
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body empty"}), 400

        #get longitude and latitude
        latitude = data.get("latitude")
        longitude = data.get("longitude")

        #data check
        if latitude is None or longitude is None:
            return jsonify({"error": "latidude and longitude are required"}), 400
        # Validate coordinate ranges
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            return jsonify({
                "error": "Latitude and longitude must be numbers"
            }), 400

        #return it
        return jsonify({
            "latitude": latitude,
            "longitude": longitude
        })
    else:
        return render_template("index.html")
