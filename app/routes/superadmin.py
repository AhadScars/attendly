"""Owner console: schools, membership codes, plan extensions."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth import require_super_admin
from app.domain import (
    create_license_key,
    create_school,
    delete_school,
    extend_school_subscription,
    get_school,
    list_license_keys,
    owner_dashboard_stats,
    revoke_license,
    set_school_active,
)

bp = Blueprint("super", __name__, url_prefix="/owner")


@bp.get("/")
@require_super_admin
def dashboard():
    stats = owner_dashboard_stats()
    return render_template("super/dashboard.html", stats=stats, schools=stats["schools"])


@bp.get("/schools")
@require_super_admin
def schools():
    stats = owner_dashboard_stats()
    return render_template("super/schools.html", schools=stats["schools"])


@bp.post("/schools/create")
@require_super_admin
def create_school_route():
    ok, msg, _school = create_school(
        request.form.get("name") or "",
        request.form.get("username") or "",
        request.form.get("password") or "",
        max_students=int(request.form.get("max_students") or 200),
    )
    flash(msg, "ok" if ok else "error")
    if ok:
        days = int(request.form.get("days") or 30)
        if days > 0 and _school:
            extend_school_subscription(_school["id"], days, "Created with opening plan")
    return redirect(url_for("super.schools"), code=303)


@bp.post("/schools/<int:school_id>/extend")
@require_super_admin
def extend(school_id: int):
    days = int(request.form.get("days") or 30)
    notes = request.form.get("notes") or ""
    seats = request.form.get("max_students")
    ok, msg = extend_school_subscription(
        school_id,
        days,
        notes,
        int(seats) if seats else None,
    )
    flash(msg, "ok" if ok else "error")
    return redirect(request.referrer or url_for("super.schools"), code=303)


@bp.post("/schools/<int:school_id>/toggle")
@require_super_admin
def toggle(school_id: int):
    school = get_school(school_id)
    if not school:
        flash("School not found.", "error")
    else:
        set_school_active(school_id, not bool(school["is_active"]))
        flash("School status updated.", "ok")
    return redirect(url_for("super.schools"), code=303)


@bp.post("/schools/<int:school_id>/delete")
@require_super_admin
def remove(school_id: int):
    ok, msg = delete_school(school_id)
    flash(msg, "ok" if ok else "error")
    return redirect(url_for("super.schools"), code=303)


@bp.get("/membership")
@require_super_admin
def membership():
    return render_template("super/licenses.html", keys=list_license_keys())


@bp.post("/membership/generate")
@require_super_admin
def generate():
    key = create_license_key(
        days_valid=int(request.form.get("days") or 30),
        max_students=int(request.form.get("max_students") or 200),
        notes=request.form.get("notes") or "",
        created_by="owner",
    )
    flash(f"New membership code: {key['key_code']}", "ok")
    return redirect(url_for("super.membership"), code=303)


@bp.post("/membership/<int:key_id>/revoke")
@require_super_admin
def revoke(key_id: int):
    ok, msg = revoke_license(key_id)
    flash(msg, "ok" if ok else "error")
    return redirect(url_for("super.membership"), code=303)
