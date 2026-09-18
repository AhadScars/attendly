"""Login and logout for owner and school operators."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import config
from app.auth import login_school, login_super_admin, logout_user
from app.domain import authenticate_admin, authenticate_school

bp = Blueprint("auth", __name__)


@bp.get("/")
def home():
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    role = (request.values.get("role") or "school").strip()
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        role = (request.form.get("role") or "school").strip()
        if role == "owner":
            admin = authenticate_admin(username, password)
            if admin:
                login_super_admin(admin)
                return redirect(url_for("super.dashboard"), code=303)
            flash("Owner username or password is incorrect.", "error")
        else:
            school = authenticate_school(username, password)
            if school:
                login_school(school)
                return redirect(url_for("school.dashboard"), code=303)
            flash("School username or password is incorrect.", "error")
    return render_template("login.html", role=role)


@bp.get("/setup")
def setup():
    return render_template("setup.html")


@bp.post("/setup/school")
def setup_school():
    url = (request.form.get("remote") or "").strip().rstrip("/")
    if not url.startswith("http://") and not url.startswith("https://"):
        flash("Enter a full URL, for example http://192.168.1.8:5055", "error")
        return redirect(url_for("auth.setup"), code=303)
    config.save_remote_server(url)
    return redirect(url, code=303)


@bp.post("/setup/owner")
def setup_owner():
    url = (request.form.get("url") or "").strip()
    key = (request.form.get("service_key") or "").strip()
    if not url or not key:
        flash("Supabase URL and service role key are required.", "error")
        return redirect(url_for("auth.setup"), code=303)
    dest = config.save_owner_env(url, key)
    return (
        "<!doctype html><title>Attendly</title>"
        "<body style='font-family:Segoe UI,sans-serif;padding:40px;max-width:640px'>"
        "<h2>Keys saved on this PC only</h2>"
        f"<p>Stored at <code>{dest}</code>. Close Attendly and open it again.</p>"
        "<p>Never copy this file into a folder you send to a school.</p></body>"
    )


@bp.post("/logout")
@bp.get("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
