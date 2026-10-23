# GET / 
# GET healthz

# IMPORTS 

#libraries
from flask import Flask, jsonify
from flask_cors import CORS

from backend.database import db, DATABASE_URL

#blue prints 
from backend.routes.api.location import location_api

######


#pre-startup configurations
app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)
       
CORS(app)

#link flask to the database
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
db.init_app(app)

with app.app_context():
    try:
        with db.engine.connect() as connection:
            print("connected to database")
    except Exception as e:
        print(f"connection failed: {e}")


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