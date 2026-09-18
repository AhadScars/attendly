"""School operator console."""
from __future__ import annotations

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from app import config
from app.auth import require_school
from app.class_sort import filter_students, unique_classes
from app.database import today_str
from app.domain import (
    add_student,
    apply_license_to_school,
    attendance_sheet,
    delete_student,
    get_school,
    get_student,
    is_school_licensed,
    list_alerts,
    list_students,
    mark_attendance,
    recent_taps,
    school_today_stats,
    send_school_alert,
    tap_student,
    update_student,
)
from app.excel_export import write_attendance_excel
from app.pagination import paginate, parse_page, parse_per_page, query_args

bp = Blueprint("school", __name__, url_prefix="/school")


def _school() -> dict:
    return get_school(session["school_id"]) or {}


@bp.before_request
def _gate():
    if session.get("role") != "school" or not session.get("school_id"):
        return redirect(url_for("auth.login"))
    if request.endpoint in {"school.membership", "school.redeem"}:
        return None
    school = _school()
    if not is_school_licensed(school):
        flash("Membership has expired. Redeem a code to continue.", "error")
        return redirect(url_for("school.membership"))


@bp.get("/")
@require_school
def dashboard():
    school = _school()
    stats = school_today_stats(school["id"])
    from app import config as app_config
    from app.domain import fcm_device_count
    from app.fcm import is_configured as fcm_configured

    return render_template(
        "school/dashboard.html",
        school=school,
        stats=stats,
        taps=recent_taps(school["id"]),
        fcm_ready=fcm_configured(),
        fcm_devices=fcm_device_count(school["id"]),
        fcm_path=str(app_config.FCM_CREDENTIALS),
    )


@bp.get("/gate")
@require_school
def gate():
    school = _school()
    return render_template(
        "school/gate.html",
        school=school,
        taps=recent_taps(school["id"], 20),
        students=list_students(school["id"])[:80],
    )


@bp.post("/gate/tap")
@require_school
def gate_tap():
    school = _school()
    payload = request.get_json(silent=True) or request.form
    query = payload.get("query") or payload.get("nfc") or ""
    action = payload.get("action") or payload.get("direction") or "auto"
    ok, msg, data = tap_student(school["id"], query, action=action, source="nfc")
    body = {
        "ok": ok,
        "message": msg,
        "data": {
            "action": data.get("action") if data else None,
            "time": data.get("time_display") if data else None,
            "student": data.get("student") if data else None,
            "message": data.get("message") if data else msg,
        }
        if data
        else None,
        "taps": recent_taps(school["id"], 20),
    }
    if request.is_json or request.headers.get("X-Requested-With") == "fetch":
        return jsonify(body), 200 if ok else 400
    flash(msg, "ok" if ok else "error")
    return redirect(url_for("school.gate"), code=303)


@bp.get("/students")
@require_school
def students():
    school = _school()
    q = request.args.get("q") or ""
    class_name = request.args.get("class") or ""
    page = parse_page(request.args.get("page"))
    per_page = parse_per_page(request.args.get("per"), 15)
    all_students = list_students(school["id"])
    filtered = filter_students(all_students, class_name=class_name or None, q=q or None)
    pager = paginate(filtered, page, per_page)
    edit = None
    edit_pk = request.args.get("edit")
    if edit_pk:
        try:
            edit = get_student(school["id"], int(edit_pk))
        except (TypeError, ValueError):
            edit = None
    return render_template(
        "school/students.html",
        school=school,
        pager=pager,
        q=q,
        class_name=class_name,
        classes=unique_classes(all_students),
        query_args=query_args,
        edit=edit,
    )


@bp.get("/students/<int:pk>/edit")
@require_school
def edit_student(pk: int):
    return redirect(url_for("school.students", edit=pk, q=request.args.get("q") or ""))


@bp.post("/students/add")
@require_school
def add():
    school = _school()
    class_name = (request.form.get("class_name") or "").strip()
    if not class_name:
        num = (request.form.get("class_num") or "").strip()
        sec = (request.form.get("section") or "").strip()
        class_name = f"{num}-{sec}" if num and sec else num
    ok, msg, _ = add_student(
        school["id"],
        request.form.get("student_id") or "",
        request.form.get("name") or "",
        class_name,
        request.form.get("parent_phone") or "",
        request.form.get("dob") or "",
        request.form.get("nfc_uid") or "",
    )
    flash(msg, "ok" if ok else "error")
    return redirect(url_for("school.students"), code=303)


@bp.post("/students/<int:pk>/update")
@require_school
def update(pk: int):
    school = _school()
    ok, msg = update_student(
        school["id"],
        pk,
        request.form.get("student_id") or "",
        request.form.get("name") or "",
        request.form.get("class_name") or "",
        request.form.get("parent_phone") or "",
        request.form.get("dob") or "",
        request.form.get("nfc_uid") or "",
    )
    flash(msg, "ok" if ok else "error")
    return redirect(url_for("school.students"), code=303)


@bp.post("/students/<int:pk>/delete")
@require_school
def remove_student(pk: int):
    ok, msg = delete_student(session["school_id"], pk)
    flash(msg, "ok" if ok else "error")
    return redirect(url_for("school.students"), code=303)


@bp.get("/attendance")
@require_school
def attendance():
    school = _school()
    date = request.args.get("date") or today_str()
    q = request.args.get("q") or ""
    class_name = request.args.get("class") or ""
    status = request.args.get("status") or ""
    page = parse_page(request.args.get("page"))
    per_page = parse_per_page(request.args.get("per"), 20)
    rows = attendance_sheet(school["id"], date)
    if class_name:
        rows = [r for r in rows if r["class_name"] == class_name]
    if q:
        needle = q.lower()
        rows = [
            r
            for r in rows
            if needle in r["name"].lower() or needle in r["student_id"].lower()
        ]
    if status == "present":
        rows = [r for r in rows if r["is_present"]]
    elif status == "absent":
        rows = [r for r in rows if not r["is_present"]]
    pager = paginate(rows, page, per_page)
    stats = school_today_stats(school["id"], date)
    return render_template(
        "school/attendance.html",
        school=school,
        pager=pager,
        date=date,
        q=q,
        class_name=class_name,
        status=status,
        stats=stats,
        classes=stats["classes"],
        query_args=query_args,
    )


@bp.post("/attendance/mark")
@require_school
def mark():
    school = _school()
    payload = request.get_json(silent=True) or request.form
    ok, msg, data = mark_attendance(
        school["id"],
        int(payload.get("student_pk")),
        action=payload.get("action") or "in",
        source="manual",
        date=payload.get("date") or today_str(),
        notify=True,
    )
    if request.is_json or request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"ok": ok, "message": msg, "data": data}), 200 if ok else 400
    flash(msg, "ok" if ok else "error")
    return redirect(url_for("school.attendance", date=payload.get("date") or today_str()), code=303)


@bp.get("/attendance/export")
@require_school
def export():
    school = _school()
    date = request.args.get("date") or today_str()
    path = write_attendance_excel(school["id"], date)
    return send_file(path, as_attachment=True, download_name=path.name)


@bp.get("/alerts")
@require_school
def alerts():
    school = _school()
    return render_template(
        "school/alerts.html",
        school=school,
        templates=config.ALERT_TEMPLATES,
        alerts=list_alerts(school["id"]),
    )


@bp.post("/alerts/send")
@require_school
def send_alert():
    school = _school()
    title = request.form.get("title") or ""
    body = request.form.get("body") or ""
    key = request.form.get("template_key") or None
    if key and not title:
        match = next((t for t in config.ALERT_TEMPLATES if t["key"] == key), None)
        if match:
            title = match["title"]
            body = body or match["body"]
    ok, msg, _ = send_school_alert(school["id"], title, body, key)
    flash(msg, "ok" if ok else "error")
    return redirect(url_for("school.alerts"), code=303)


@bp.get("/membership")
@require_school
def membership():
    return render_template("school/membership.html", school=_school())


@bp.post("/membership/redeem")
@require_school
def redeem():
    ok, msg = apply_license_to_school(session["school_id"], request.form.get("code") or "")
    flash(msg, "ok" if ok else "error")
    return redirect(url_for("school.membership"), code=303)
