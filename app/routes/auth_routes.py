"""Login and logout for owner and school operators."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

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


@bp.post("/logout")
@bp.get("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
