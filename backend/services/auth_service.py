import hmac
import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import g, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from backend.database import db
from backend.models import Guardian, Users
from backend.services.exceptions import AuthenticationError, ConflictError
from backend.services.user_service import get_user_and_role, get_user_by_identifier, get_user_role
from backend.services.validation import (
    validate_email,
    validate_password,
    validate_phone_number,
    validate_username,
)


def _safe_check_password(password_hash: str, password: str) -> bool:
    """Verify a Werkzeug password hash, returning False on malformed legacy hashes."""
    if not password_hash or not password:
        return False
    try:
        return check_password_hash(password_hash, password)
    except ValueError:
        return False


def register_guardian(
    username: str | None,
    email: str | None,
    phone_number: str | None,
    password: str | None,
    confirm_password: str | None = None,
) -> Users:
    """Register a new guardian user and profile in a single transaction."""
    clean_username = validate_username(username)
    clean_email = validate_email(email)
    clean_phone = validate_phone_number(phone_number)
    clean_password = validate_password(password, confirm_password)

    existing_username = Users.query.filter_by(username=clean_username).first()
    if existing_username is not None:
        raise ConflictError("Username is already in use.")

    existing_email = Users.query.filter_by(email=clean_email).first()
    if existing_email is not None:
        raise ConflictError("Email is already registered.")

    user = Users(
        username=clean_username,
        password_hash=generate_password_hash(clean_password),
        email=clean_email,
        phone_number=clean_phone,
    )
    try:
        db.session.add(user)
        db.session.flush()

        guardian = Guardian(
            user_id=user.user_id,
            longitude=None,
            latitude=None,
            location_updated_at=None,
        )
        db.session.add(guardian)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ConflictError("An account with that username or email already exists.")
    except Exception:
        db.session.rollback()
        raise

    return user


def authenticate_user(identifier: str | None, password: str | None) -> tuple[Users, str]:
    """Verify credentials and return (Users, role) for guardian or child."""
    if not isinstance(identifier, str) or not identifier.strip() or not isinstance(password, str):
        raise AuthenticationError("Username/email and password are required.")

    user = get_user_by_identifier(identifier)
    if user is None or not _safe_check_password(user.password_hash, password):
        raise AuthenticationError("Invalid username/email or password.")

    role = get_user_role(user.user_id)
    if role is None:
        raise AuthenticationError("Account has no assigned role.")

    return user, role


def get_csrf_token() -> str:
    """Retrieve or lazily initialize the CSRF token for the active Flask session."""
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def rotate_csrf_token() -> str:
    """Generate a fresh CSRF token (called on authentication state changes)."""
    token = secrets.token_urlsafe(32)
    session["csrf_token"] = token
    return token


def verify_csrf_token(submitted_token: str | None) -> bool:
    """Constant-time validation of a submitted CSRF token against the session token."""
    expected = session.get("csrf_token")
    if not expected or not isinstance(submitted_token, str) or not submitted_token:
        return False
    return hmac.compare_digest(expected, submitted_token)


def login_session(user: Users, role: str) -> None:
    """Establish authenticated session state for a verified user."""
    session.clear()
    session["user_id"] = str(user.user_id)
    session["role"] = role
    session["username"] = user.username
    rotate_csrf_token()


def logout_session() -> None:
    """Clear the authenticated session."""
    session.clear()


def is_safe_redirect_target(target: str | None) -> bool:
    """Ensure next redirect URL stays on the same origin without scheme/netloc."""
    if not target or not isinstance(target, str):
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc and target.startswith("/") and not target.startswith("//")


def _is_api_request() -> bool:
    return request.path.startswith("/api/")


def _load_authenticated_user() -> tuple[Users | None, str | None]:
    user_id = session.get("user_id")
    if not user_id:
        return None, None
    user, role = get_user_and_role(user_id)
    if user is None or role is None:
        session.clear()
        return None, None
    return user, role


def login_required(view_func):
    """Require an authenticated user session; redirect pages to login or return 401 for APIs."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        user, role = _load_authenticated_user()
        if user is None:
            if _is_api_request():
                return jsonify({"error": "Authentication required."}), 401
            next_url = request.full_path.rstrip("?")
            return redirect(url_for("auth_web.login", next=next_url))

        g.current_user = user
        g.current_role = role
        return view_func(*args, **kwargs)

    return wrapped


def role_required(*allowed_roles: str):
    """Require the authenticated user's database role to match one of allowed_roles."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(*args, **kwargs):
            if g.current_role not in allowed_roles:
                if _is_api_request():
                    return jsonify({"error": "Access denied for your account role."}), 403
                return (
                    render_template(
                        "error.html",
                        status_code=403,
                        title="Access Forbidden",
                        message="You do not have permission to view this page.",
                    ),
                    403,
                )
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


guardian_required = role_required("guardian")
child_required = role_required("child")
