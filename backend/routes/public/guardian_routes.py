from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from backend.models import Guardian
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
)
from backend.services.exceptions import ServiceError
from backend.services.monitoring_service import get_guardian_dashboard_data

guardian_web = Blueprint("guardian_web", __name__)


@guardian_web.route("/dashboard")
@guardian_required
def dashboard():
    data = get_guardian_dashboard_data(g.current_user.user_id)
    return render_template("dashboard.html", dashboard=data)


@guardian_web.route("/children")
@guardian_required
def children():
    data = get_guardian_dashboard_data(g.current_user.user_id)
    return render_template("children.html", dashboard=data)


@guardian_web.route("/children/add", methods=["GET", "POST"])
@guardian_required
def add_child():
    if request.method == "POST":
        username = request.form.get("username", "")
        email = request.form.get("email", "")
        phone_number = request.form.get("phone_number", "")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        try:
            create_child_for_guardian(
                guardian_id=g.current_user.user_id,
                username=username,
                email=email,
                phone_number=phone_number,
                password=password,
                confirm_password=confirm_password,
            )
        except ServiceError as exc:
            return (
                render_template(
                    "add_child.html",
                    error=exc.message,
                    form_data={
                        "username": username,
                        "email": email,
                        "phone_number": phone_number,
                    },
                ),
                exc.status_code,
            )

        flash(f"Child account '{username.strip()}' added and associated with your profile.", "success")
        return redirect(url_for("guardian_web.children"))

    return render_template("add_child.html", form_data={})


@guardian_web.route("/children/<child_id>")
@guardian_required
def child_detail(child_id):
    detail = get_child_detail_for_guardian(g.current_user.user_id, child_id)
    return render_template("child_detail.html", detail=detail)


@guardian_web.route("/bases")
@guardian_required
def bases():
    guardian = Guardian.query.filter_by(user_id=g.current_user.user_id).first()
    guardian_bases = [b.to_dict() for b in list_guardian_bases(g.current_user.user_id)]
    return render_template(
        "bases.html",
        bases=guardian_bases,
        guardian=guardian.to_dict() if guardian else {},
    )


@guardian_web.route("/bases/add", methods=["GET", "POST"])
@guardian_required
def add_base():
    guardian = Guardian.query.filter_by(user_id=g.current_user.user_id).first()
    default_lat = guardian.latitude if guardian and guardian.latitude is not None else 37.3382
    default_lon = guardian.longitude if guardian and guardian.longitude is not None else -121.8863

    if request.method == "POST":
        base_name = request.form.get("base_name", "")
        latitude = request.form.get("latitude", "")
        longitude = request.form.get("longitude", "")
        warning_radius = request.form.get("warning_radius", "")
        danger_radius = request.form.get("danger_radius", "")

        try:
            create_base(
                guardian_id=g.current_user.user_id,
                base_name=base_name,
                latitude=latitude,
                longitude=longitude,
                warning_radius=warning_radius,
                danger_radius=danger_radius,
            )
        except ServiceError as exc:
            return (
                render_template(
                    "base_form.html",
                    mode="add",
                    error=exc.message,
                    form_data={
                        "base_name": base_name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "warning_radius": warning_radius,
                        "danger_radius": danger_radius,
                    },
                    default_lat=default_lat,
                    default_lon=default_lon,
                ),
                exc.status_code,
            )

        flash(f"Base '{base_name.strip()}' saved and applied to your monitored children.", "success")
        return redirect(url_for("guardian_web.bases"))

    return render_template(
        "base_form.html",
        mode="add",
        form_data={
            "base_name": "",
            "latitude": f"{default_lat:.6f}",
            "longitude": f"{default_lon:.6f}",
            "warning_radius": 200,
            "danger_radius": 500,
        },
        default_lat=default_lat,
        default_lon=default_lon,
    )


@guardian_web.route("/bases/<base_id>/edit", methods=["GET", "POST"])
@guardian_required
def edit_base(base_id):
    base = get_guardian_base(g.current_user.user_id, base_id)
    if request.method == "POST":
        base_name = request.form.get("base_name", "")
        latitude = request.form.get("latitude", "")
        longitude = request.form.get("longitude", "")
        warning_radius = request.form.get("warning_radius", "")
        danger_radius = request.form.get("danger_radius", "")

        try:
            update_base(
                guardian_id=g.current_user.user_id,
                base_id=base_id,
                base_name=base_name,
                latitude=latitude,
                longitude=longitude,
                warning_radius=warning_radius,
                danger_radius=danger_radius,
            )
        except ServiceError as exc:
            return (
                render_template(
                    "base_form.html",
                    mode="edit",
                    base=base.to_dict(),
                    error=exc.message,
                    form_data={
                        "base_name": base_name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "warning_radius": warning_radius,
                        "danger_radius": danger_radius,
                    },
                    default_lat=base.latitude,
                    default_lon=base.longitude,
                ),
                exc.status_code,
            )

        flash(f"Base '{base_name.strip()}' updated.", "success")
        return redirect(url_for("guardian_web.bases"))

    return render_template(
        "base_form.html",
        mode="edit",
        base=base.to_dict(),
        form_data={
            "base_name": base.base_name,
            "latitude": f"{base.latitude:.6f}",
            "longitude": f"{base.longitude:.6f}",
            "warning_radius": base.warning_radius,
            "danger_radius": base.danger_radius,
        },
        default_lat=base.latitude,
        default_lon=base.longitude,
    )


@guardian_web.route("/bases/<base_id>/delete", methods=["POST"])
@guardian_required
def delete_base_route(base_id):
    delete_base(g.current_user.user_id, base_id)
    flash("Base location deleted.", "info")
    return redirect(url_for("guardian_web.bases"))
