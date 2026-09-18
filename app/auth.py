"""Password hashing and session helpers."""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional

from flask import jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def login_super_admin(admin: dict[str, Any]) -> None:
    session.clear()
    session["role"] = "super_admin"
    session["username"] = admin["username"]
    session["name"] = admin["name"]


def login_school(school: dict[str, Any]) -> None:
    session.clear()
    session["role"] = "school"
    session["school_id"] = school["id"]
    session["username"] = school["username"]
    session["name"] = school["name"]


def logout_user() -> None:
    session.clear()


def current_role() -> Optional[str]:
    return session.get("role")


def current_school_id() -> Optional[int]:
    return session.get("school_id")


def require_super_admin(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "super_admin":
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)

    return wrapper


def require_school(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "school" or not session.get("school_id"):
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)

    return wrapper


def parent_bearer() -> str:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return (request.args.get("token") or "").strip()


def require_parent(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from app.domain import get_parent_session

        sess = get_parent_session(parent_bearer())
        if not sess:
            return jsonify({"ok": False, "error": "Please sign in again."}), 401
        request.parent_session = sess
        return fn(*args, **kwargs)

    return wrapper
