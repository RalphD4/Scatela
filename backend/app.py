# GET / 
# GET healthz

from flask import Flask, jsonify
from flask_cors import CORS



#pre-startup configurations
app = Flask(__name__)
CORS(app)


#blue-print registrations

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
        use_reloader=False
    )