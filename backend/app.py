import os
import secrets

from flask import Flask, jsonify, render_template, request, session
from flask_cors import CORS

from backend.database import DATABASE_URL, db
import backend.models  # noqa: F401 - register SQLAlchemy models
from backend.routes.api import geocode_api, guardian_api, location_api
from backend.routes.public import auth_web, child_web, guardian_web
from backend.services.auth_service import (
    _load_authenticated_user,
    get_csrf_token,
    verify_csrf_token,
)
from backend.services.exceptions import ServiceError


def create_app(config_overrides: dict | None = None) -> Flask:
    """Create and configure the Scatela Flask application."""
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
    )

    secret_key = os.getenv("SECRET_KEY") or os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
    app.config.from_mapping(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=DATABASE_URL,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        CSRF_ENABLED=True,
    )
    if config_overrides:
        app.config.update(config_overrides)

    # Keep CORS restricted to health checks; session-authenticated views use same-origin cookies
    CORS(app, resources={r"/healthz": {"origins": "*"}})

    db.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_web)
    app.register_blueprint(guardian_web)
    app.register_blueprint(child_web)
    app.register_blueprint(location_api)
    app.register_blueprint(guardian_api)
    app.register_blueprint(geocode_api)

    @app.before_request
    def enforce_csrf_protection():
        if not app.config.get("CSRF_ENABLED", True):
            return None
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return None

        # Let unauthenticated /api/* requests return 401 from @login_required rather than 403 CSRF
        if request.path.startswith("/api/") and "user_id" not in session:
            return None

        json_body = request.get_json(silent=True)
        json_token = json_body.get("csrf_token") if isinstance(json_body, dict) else None
        submitted = (
            request.headers.get("X-CSRF-Token")
            or request.form.get("csrf_token")
            or json_token
        )
        if not verify_csrf_token(submitted):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Invalid or missing CSRF token."}), 403
            return (
                render_template(
                    "error.html",
                    status_code=403,
                    title="Security Verification Failed",
                    message="Your form session expired or could not be verified. Please refresh and try again.",
                ),
                403,
            )
        return None

    @app.context_processor
    def inject_template_globals():
        user, role = _load_authenticated_user()
        return {
            "csrf_token": get_csrf_token(),
            "current_user": user,
            "current_role": role,
        }

    @app.route("/healthz")
    def healthz():
        return jsonify({"status": "ok"}), 200

    @app.errorhandler(ServiceError)
    def handle_service_error(exc: ServiceError):
        if request.path.startswith("/api/"):
            return jsonify({"error": exc.message}), exc.status_code
        return (
            render_template(
                "error.html",
                status_code=exc.status_code,
                title="Request Error",
                message=exc.message,
            ),
            exc.status_code,
        )

    @app.errorhandler(404)
    def handle_not_found(_exc):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Endpoint not found."}), 404
        return (
            render_template(
                "error.html",
                status_code=404,
                title="Page Not Found",
                message="The page you requested could not be found.",
            ),
            404,
        )

    @app.errorhandler(405)
    def handle_method_not_allowed(_exc):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Method not allowed."}), 405
        return (
            render_template(
                "error.html",
                status_code=405,
                title="Method Not Allowed",
                message="That action is not supported for this page.",
            ),
            405,
        )

    @app.errorhandler(500)
    def handle_internal_error(_exc):
        db.session.rollback()
        if request.path.startswith("/api/"):
            return jsonify({"error": "An unexpected server error occurred."}), 500
        return (
            render_template(
                "error.html",
                status_code=500,
                title="Server Error",
                message="An unexpected error occurred. Please try again later.",
            ),
            500,
        )

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        try:
            with db.engine.connect():
                print("Connected to database")
        except Exception:
            print("Database connection failed at startup")

    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
        use_reloader=True,
    )
