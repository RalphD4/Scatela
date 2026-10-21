# GET / 
# GET healthz

# IMPORTS 

#libraries
from flask import Flask, jsonify
from flask_cors import CORS

#blue prints
from backend.routes.api.location import location_api

#####


#pre-startup configurations
app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)
       
CORS(app)


#blue-print registrations

app.register_blueprint(location_api)



#home routes
@app.route("/")
def home():
    return jsonify("Welcome to Scatela")


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


#start the app
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
        use_reloader=True
    )