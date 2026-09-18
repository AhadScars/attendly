"""JSON API for the Attendly parent Android app."""
from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request

from app.auth import parent_bearer, require_parent
from app.database import today_str
from app.domain import (
    delete_parent_session,
    list_alerts,
    month_attendance,
    parent_login,
    parent_notifications,
    parent_today,
    save_fcm_token,
    search_schools_public,
    switch_parent_child,
)
from app.fcm import is_configured as fcm_configured

bp = Blueprint("parent_api", __name__, url_prefix="/api/parent")


def _sess():
    return request.parent_session


def _ok(data=None, message=""):
    body = {"ok": True}
    if message:
        body["message"] = message
    if data is not None:
        body.update(data)
    return jsonify(body)


def _err(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


@bp.get("/health")
def health():
    return _ok(
        {
            "service": "attendly",
            "time": datetime.now().isoformat(timespec="seconds"),
            "fcm": fcm_configured(),
        }
    )


@bp.get("/schools")
def schools():
    return _ok({"schools": search_schools_public(request.args.get("q") or "")})


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or request.form
    ok, msg, data = parent_login(
        payload.get("school_name") or payload.get("school") or "",
        payload.get("phone") or payload.get("username") or "",
        payload.get("dob") or payload.get("password") or "",
    )
    if not ok:
        return _err(msg, 401)
    return _ok(data, msg)


@bp.post("/logout")
@require_parent
def logout():
    delete_parent_session(parent_bearer())
    return _ok(message="Signed out.")


@bp.get("/me")
@require_parent
def me():
    sess = _sess()
    return _ok(
        {
            "school": {"id": sess["school"]["id"], "name": sess["school"]["name"]},
            "phone": sess["parent_phone"],
            "children": [
                {
                    "id": c["id"],
                    "student_id": c["student_id"],
                    "name": c["name"],
                    "class_name": c["class_name"],
                    "dob_display": c.get("dob_display"),
                }
                for c in sess["children"]
            ],
            "selected": {
                "id": sess["selected"]["id"],
                "student_id": sess["selected"]["student_id"],
                "name": sess["selected"]["name"],
                "class_name": sess["selected"]["class_name"],
                "dob_display": sess["selected"].get("dob_display"),
            }
            if sess.get("selected")
            else None,
        }
    )


@bp.post("/switch")
@require_parent
def switch():
    payload = request.get_json(silent=True) or request.form
    ok, msg, sess = switch_parent_child(parent_bearer(), int(payload.get("student_id") or 0))
    if not ok:
        return _err(msg)
    child = sess["selected"]
    body = {
        "selected": {
            "id": child["id"],
            "student_id": child["student_id"],
            "name": child["name"],
            "class_name": child["class_name"],
        }
    }
    if sess.get("token"):
        body["token"] = sess["token"]
    return _ok(body, msg)


@bp.get("/today")
@require_parent
def today():
    sess = _sess()
    if not sess.get("selected"):
        return _err("No child selected.")
    return _ok(parent_today(sess["school_id"], sess["selected"]["id"]))


@bp.get("/attendance")
@require_parent
def attendance():
    sess = _sess()
    if not sess.get("selected"):
        return _err("No child selected.")
    now = datetime.now()
    year = int(request.args.get("year") or now.year)
    month = int(request.args.get("month") or now.month)
    data = month_attendance(sess["school_id"], sess["selected"]["id"], year, month)
    student = data.pop("student")
    return _ok(
        {
            "student": {
                "id": student["id"],
                "name": student["name"],
                "class_name": student["class_name"],
            }
            if student
            else None,
            **data,
        }
    )


@bp.get("/alerts")
@require_parent
def alerts():
    sess = _sess()
    return _ok({"alerts": list_alerts(sess["school_id"], 60)})


@bp.get("/notifications")
@require_parent
def notifications():
    sess = _sess()
    since = int(request.args.get("since_id") or 0)
    items = parent_notifications(
        sess["school_id"],
        sess["parent_phone"],
        since_id=since,
        student_pk=sess["selected"]["id"] if sess.get("selected") else None,
    )
    return _ok({"notifications": items, "today": today_str(), "fcm": fcm_configured()})


@bp.post("/fcm-token")
@require_parent
def register_fcm():
    sess = _sess()
    payload = request.get_json(silent=True) or request.form
    ok, msg = save_fcm_token(
        sess["school_id"],
        sess["parent_phone"],
        payload.get("token") or "",
    )
    if not ok:
        return _err(msg)
    return _ok({"fcm": fcm_configured()}, msg)
