from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.services.auth_service import (
    _load_authenticated_user,
    authenticate_user,
    is_safe_redirect_target,
    login_session,
    logout_session,
    register_guardian,
)
from backend.services.exceptions import ServiceError

auth_web = Blueprint("auth_web", __name__)


def _redirect_for_role(role: str):
    if role == "guardian":
        return redirect(url_for("guardian_web.dashboard"))
    return redirect(url_for("child_web.tracker"))


@auth_web.route("/")
def home():
    user, role = _load_authenticated_user()
    if user is not None and role is not None:
        return _redirect_for_role(role)
    return redirect(url_for("auth_web.login"))


@auth_web.route("/login", methods=["GET", "POST"])
def login():
    user, role = _load_authenticated_user()
    if user is not None and role is not None:
        return _redirect_for_role(role)

    next_url = request.args.get("next") or request.form.get("next") or ""
    if request.method == "POST":
        identifier = request.form.get("identifier", "")
        password = request.form.get("password", "")
        try:
            user, role = authenticate_user(identifier, password)
        except ServiceError as exc:
            return (
                render_template(
                    "login.html",
                    error=exc.message,
                    identifier=identifier,
                    next_url=next_url,
                ),
                exc.status_code,
            )

        login_session(user, role)
        if is_safe_redirect_target(next_url):
            return redirect(next_url)
        return _redirect_for_role(role)

    return render_template("login.html", identifier="", next_url=next_url)


@auth_web.route("/register", methods=["GET", "POST"])
def register():
    user, role = _load_authenticated_user()
    if user is not None and role is not None:
        return _redirect_for_role(role)

    if request.method == "POST":
        username = request.form.get("username", "")
        email = request.form.get("email", "")
        phone_number = request.form.get("phone_number", "")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        try:
            new_user = register_guardian(
                username=username,
                email=email,
                phone_number=phone_number,
                password=password,
                confirm_password=confirm_password,
            )
        except ServiceError as exc:
            return (
                render_template(
                    "register.html",
                    error=exc.message,
                    form_data={
                        "username": username,
                        "email": email,
                        "phone_number": phone_number,
                    },
                ),
                exc.status_code,
            )

        login_session(new_user, "guardian")
        flash("Guardian account created. Automatic location tracking is enabled.", "success")
        return redirect(url_for("guardian_web.dashboard"))

    return render_template("register.html", form_data={})


@auth_web.route("/logout", methods=["POST"])
def logout():
    logout_session()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth_web.login"))
