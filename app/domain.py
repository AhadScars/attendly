"""Attendly domain — all data in Supabase. No local database."""
from __future__ import annotations

import calendar
import hashlib
import hmac
import json
import re
import secrets
import string
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta
from typing import Any, Optional

from app import config
from app.auth import hash_password, verify_password
from app.class_sort import filter_students, sort_students, unique_classes
from app.database import (
    combine_local,
    format_ampm,
    local_now,
    local_time_ampm,
    local_time_str,
    naive,
    now_iso,
    today_str,
)
from app.store import count, delete, ins, sb, sel, sel_one, upd


def _digits(phone: str) -> str:
    return re.sub(r"\D+", "", phone or "")


def normalize_phone(phone: str) -> str:
    digits = _digits(phone)
    return digits[-10:] if len(digits) >= 10 else digits


def normalize_dob(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def format_dob(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.strptime(str(iso)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(iso)


def new_nfc_uid() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "AT" + "".join(secrets.choice(alphabet) for _ in range(8))


def generate_license_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4))


def parse_expiry(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("T", " ").replace("Z", "")
    text = text.split("+")[0].strip()[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19] if " " in text else text[:10], fmt)
        except ValueError:
            continue
    return None


def days_remaining(expires_at: str | None) -> int:
    exp = parse_expiry(expires_at)
    if not exp:
        return 0
    return max(0, (exp.date() - local_now().date()).days)


def is_school_licensed(school: dict[str, Any] | None) -> bool:
    if not school or not school.get("is_active"):
        return False
    exp = parse_expiry(school.get("license_expires_at"))
    return bool(exp and naive(exp) >= naive(local_now()))


def decorate_school(school: dict[str, Any]) -> dict[str, Any]:
    school["days_left"] = days_remaining(school.get("license_expires_at"))
    school["licensed"] = is_school_licensed(school)
    school["is_active"] = 1 if school.get("is_active") else 0
    return school


def _student(row: dict | None) -> dict | None:
    if not row:
        return None
    row = dict(row)
    row["dob_display"] = format_dob(row.get("dob"))
    row["is_active"] = 1
    return row


def get_admin_by_username(username: str) -> Optional[dict]:
    return sel_one("admins", username=username.strip().lower())


def authenticate_admin(username: str, password: str) -> Optional[dict]:
    admin = get_admin_by_username(username)
    if not admin or not verify_password(admin["password_hash"], password):
        return None
    return admin


def ensure_super_admin() -> None:
    if get_admin_by_username(config.SUPER_ADMIN_USER):
        return
    ins(
        "admins",
        {
            "username": config.SUPER_ADMIN_USER.lower(),
            "password_hash": hash_password(config.SUPER_ADMIN_PASS),
            "name": config.SUPER_ADMIN_NAME,
        },
    )


def create_school(
    name: str,
    username: str,
    password: str,
    license_key: str | None = None,
    license_expires_at: str | None = None,
    max_students: int = 200,
) -> tuple[bool, str, Optional[dict]]:
    name = name.strip()
    username = username.strip().lower()
    if not name or not username or not password:
        return False, "School name, username and password are required.", None
    if len(password) < 6:
        return False, "Password must be at least 6 characters.", None
    if sel_one("schools", username=username):
        return False, "That school username is already taken.", None
    row = ins(
        "schools",
        {
            "name": name,
            "username": username,
            "password_hash": hash_password(password),
            "license_expires_at": license_expires_at,
            "max_students": max_students,
            "is_active": True,
        },
    )
    return True, "School created.", decorate_school(row)


def authenticate_school(username: str, password: str) -> Optional[dict]:
    row = sel_one("schools", username=username.strip().lower())
    if not row or not verify_password(row["password_hash"], password):
        return None
    return decorate_school(row)


def get_school(school_id: int) -> Optional[dict]:
    row = sel_one("schools", id=school_id)
    return decorate_school(row) if row else None


def find_school_by_name(name: str) -> Optional[dict]:
    needle = (name or "").strip().lower()
    if not needle:
        return None
    rows = sb().table("schools").select("*").eq("is_active", True).execute().data or []
    exact = [r for r in rows if r["name"].lower() == needle or r["username"].lower() == needle]
    if exact:
        return decorate_school(exact[0])
    matches = [r for r in rows if needle in r["name"].lower()]
    return decorate_school(matches[0]) if len(matches) == 1 else None


def list_schools() -> list[dict]:
    rows = sb().table("schools").select("*").order("name").execute().data or []
    out = []
    for row in rows:
        item = decorate_school(row)
        item["student_count"] = count("students", school_id=row["id"])
        out.append(item)
    return out


def set_school_active(school_id: int, active: bool) -> None:
    upd("schools", {"is_active": bool(active)}, id=school_id)


def delete_school(school_id: int) -> tuple[bool, str]:
    delete("fcm_tokens", school_id=school_id)
    delete("alerts", school_id=school_id)
    delete("attendance", school_id=school_id)
    delete("students", school_id=school_id)
    upd("license_keys", {"school_id": None}, school_id=school_id)
    delete("schools", id=school_id)
    return True, "School deleted."


def update_school_password(school_id: int, new_password: str) -> tuple[bool, str]:
    if len(new_password) < 6:
        return False, "Password must be at least 6 characters."
    upd("schools", {"password_hash": hash_password(new_password)}, id=school_id)
    return True, "Password updated."


def owner_dashboard_stats() -> dict[str, Any]:
    schools = list_schools()
    active = [s for s in schools if s.get("is_active")]
    licensed = [s for s in active if s.get("licensed")]
    unused = [
        k
        for k in sel("license_keys")
        if not k.get("school_id") and not k.get("is_revoked")
    ]
    return {
        "total_schools": len(schools),
        "active_schools": len(active),
        "licensed_schools": len(licensed),
        "expiring_soon": len([s for s in licensed if 0 < s["days_left"] <= 14]),
        "expired_schools": len([s for s in active if not s.get("licensed")]),
        "total_students": count("students"),
        "unused_keys": len(unused),
        "schools": schools,
    }


def create_license_key(
    days_valid: int = 30,
    max_students: int = 200,
    notes: str = "",
    created_by: str = "owner",
) -> dict[str, Any]:
    row = {
        "key_code": generate_license_code(),
        "days_valid": max(1, int(days_valid)),
        "max_students": max(1, int(max_students)),
        "notes": notes.strip() or None,
        "is_revoked": False,
    }
    return ins("license_keys", row)


def list_license_keys() -> list[dict[str, Any]]:
    keys = sb().table("license_keys").select("*").order("id", desc=True).execute().data or []
    schools = {s["id"]: s for s in sel("schools", "id,name,username")}
    for key in keys:
        school = schools.get(key.get("school_id"))
        key["school_name"] = school["name"] if school else None
        key["school_username"] = school["username"] if school else None
    return keys


def apply_license_to_school(school_id: int, key_code: str) -> tuple[bool, str]:
    key_code = (key_code or "").strip().upper().replace(" ", "")
    if not key_code:
        return False, "Enter a membership code."
    lic = sel_one("license_keys", key_code=key_code)
    if not lic:
        return False, "This membership code is not valid."
    if lic.get("is_revoked"):
        return False, "This membership code has been revoked."
    if lic.get("school_id") and lic["school_id"] != school_id:
        return False, "This membership code is already used by another school."
    if lic.get("school_id") == school_id and lic.get("used_at"):
        return False, "This membership code is already applied to your school."
    school = sel_one("schools", id=school_id)
    if not school:
        return False, "School not found."
    days = int(lic["days_valid"])
    now = local_now()
    base = now
    current = parse_expiry(school.get("license_expires_at"))
    if current and current > now:
        base = current
    new_exp = base + timedelta(days=days)
    seats = int(lic.get("max_students") or school.get("max_students") or 200)
    upd(
        "schools",
        {
            "license_expires_at": new_exp.isoformat(),
            "max_students": seats,
            "is_active": True,
        },
        id=school_id,
    )
    upd(
        "license_keys",
        {"school_id": school_id, "used_at": now.isoformat()},
        id=lic["id"],
    )
    return True, f"Membership activated until {new_exp.strftime('%d %b %Y')}."


def extend_school_subscription(
    school_id: int, days: int, notes: str = "", max_students: int | None = None
) -> tuple[bool, str]:
    days = int(days)
    if days < 1:
        return False, "Days must be at least 1."
    school = sel_one("schools", id=school_id)
    if not school:
        return False, "School not found."
    now = local_now()
    base = now
    current = parse_expiry(school.get("license_expires_at"))
    if current and current > now:
        base = current
    new_exp = base + timedelta(days=days)
    seats = int(max_students or school.get("max_students") or 200)
    key = ins(
        "license_keys",
        {
            "key_code": generate_license_code(),
            "days_valid": days,
            "max_students": seats,
            "school_id": school_id,
            "used_at": now.isoformat(),
            "notes": notes or f"+{days}d",
            "is_revoked": False,
        },
    )
    upd(
        "schools",
        {
            "license_expires_at": new_exp.isoformat(),
            "max_students": seats,
            "is_active": True,
        },
        id=school_id,
    )
    _ = key
    return True, f"Plan extended until {new_exp.strftime('%d %b %Y')}."


def revoke_license(key_id: int) -> tuple[bool, str]:
    if not sel_one("license_keys", id=key_id):
        return False, "Membership code not found."
    upd("license_keys", {"is_revoked": True}, id=key_id)
    return True, "Membership code revoked."


def list_students(school_id: int) -> list[dict]:
    from app.offline import cache_students, cached_students, is_network_error

    try:
        rows = (
            sb()
            .table("students")
            .select("*")
            .eq("school_id", school_id)
            .order("name")
            .execute()
            .data
            or []
        )
        students = sort_students([_student(r) for r in rows])
        cache_students(school_id, students)
        return students
    except Exception as exc:
        if not is_network_error(exc):
            raise
        cached = [_student(r) for r in cached_students(school_id)]
        return sort_students(cached)


def get_student(school_id: int, pk: int) -> Optional[dict]:
    from app.offline import cached_student, is_network_error

    try:
        return _student(sel_one("students", id=pk, school_id=school_id))
    except Exception as exc:
        if not is_network_error(exc):
            raise
        return _student(cached_student(school_id, pk))


def student_count(school_id: int) -> int:
    return count("students", school_id=school_id)


def add_student(
    school_id: int,
    student_id: str,
    name: str,
    class_name: str,
    parent_phone: str,
    dob: str,
    nfc_uid: str | None = None,
) -> tuple[bool, str, Optional[dict]]:
    student_id = (student_id or "").strip().upper()
    name = (name or "").strip()
    class_name = (class_name or "").strip()
    parent_phone = normalize_phone(parent_phone)
    dob_iso = normalize_dob(dob)
    nfc_uid = (nfc_uid or "").strip().upper() or new_nfc_uid()
    if not student_id or not name or not class_name:
        return False, "Student ID, name and class are required.", None
    if len(parent_phone) != 10:
        return False, "Parent phone must be a 10-digit mobile number.", None
    if not dob_iso:
        return False, "Enter date of birth as DD/MM/YYYY.", None
    school = get_school(school_id)
    if school and student_count(school_id) >= int(school.get("max_students") or 200):
        return False, "Student limit for this membership has been reached.", None
    try:
        row = ins(
            "students",
            {
                "school_id": school_id,
                "student_id": student_id,
                "name": name,
                "class_name": class_name,
                "parent_phone": parent_phone,
                "dob": dob_iso,
                "nfc_uid": nfc_uid,
            },
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "nfc" in msg:
            return False, "This NFC tag is already assigned.", None
        if "unique" in msg or "duplicate" in msg:
            return False, "Student ID already exists in this school.", None
        raise
    return True, "Student added.", _student(row)


def update_student(
    school_id: int,
    pk: int,
    student_id: str,
    name: str,
    class_name: str,
    parent_phone: str,
    dob: str,
    nfc_uid: str,
) -> tuple[bool, str]:
    student_id = (student_id or "").strip().upper()
    name = (name or "").strip()
    class_name = (class_name or "").strip()
    parent_phone = normalize_phone(parent_phone)
    dob_iso = normalize_dob(dob)
    nfc_uid = (nfc_uid or "").strip().upper() or new_nfc_uid()
    if not student_id or not name or not class_name:
        return False, "Student ID, name and class are required."
    if len(parent_phone) != 10:
        return False, "Parent phone must be a 10-digit mobile number."
    if not dob_iso:
        return False, "Enter date of birth as DD/MM/YYYY."
    try:
        upd(
            "students",
            {
                "student_id": student_id,
                "name": name,
                "class_name": class_name,
                "parent_phone": parent_phone,
                "dob": dob_iso,
                "nfc_uid": nfc_uid,
            },
            id=pk,
            school_id=school_id,
        )
    except Exception as exc:
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            return False, "Student ID or NFC tag is already in use."
        raise
    return True, "Student updated."


def delete_student(school_id: int, pk: int) -> tuple[bool, str]:
    delete("attendance", school_id=school_id, student_pk=pk)
    delete("students", id=pk, school_id=school_id)
    return True, "Student removed."


def find_student_for_tap(school_id: int, query: str) -> tuple[Optional[dict], str]:
    from app.offline import cached_students, is_network_error

    q = (query or "").strip()
    if not q:
        return None, "Enter an NFC tag or student ID."
    try:
        row = sel_one("students", school_id=school_id, nfc_uid=q.upper())
        if row:
            return _student(row), ""
        row = sel_one("students", school_id=school_id, student_id=q.upper())
        if row:
            return _student(row), ""
        rows = (
            sb()
            .table("students")
            .select("*")
            .eq("school_id", school_id)
            .ilike("name", f"%{q}%")
            .execute()
            .data
            or []
        )
    except Exception as exc:
        if not is_network_error(exc):
            raise
        rows = cached_students(school_id)
        needle = q.upper()
        exact = [
            r
            for r in rows
            if str(r.get("nfc_uid", "")).upper() == needle or str(r.get("student_id", "")).upper() == needle
        ]
        if len(exact) == 1:
            return _student(exact[0]), ""
        rows = [r for r in rows if q.lower() in str(r.get("name", "")).lower()]
    if len(rows) == 1:
        return _student(rows[0]), ""
    if len(rows) > 1:
        return None, "Several students match that name. Use the NFC tag or student ID."
    return None, "No student found for that tag."


def _today_att(school_id: int, student_pk: int, date: str) -> Optional[dict]:
    from app.offline import is_network_error, local_attendance

    remote = None
    try:
        remote = sel_one("attendance", school_id=school_id, student_pk=student_pk, day=date)
    except Exception as exc:
        if not is_network_error(exc):
            raise
    local_rows = local_attendance(school_id, student_pk, date)
    local = local_rows[0] if local_rows else None
    if local and local.get("pending"):
        return local
    return local or remote


def _cooldown_ok(date: str, last_time: str | None, minutes: int) -> tuple[bool, str]:
    if not last_time or minutes <= 0:
        return True, ""
    stamped = combine_local(date, last_time)
    if not stamped:
        return True, ""
    wait_until = stamped + timedelta(minutes=minutes)
    if local_now() < wait_until:
        remain = int((wait_until - local_now()).total_seconds() // 60) + 1
        return False, f"Please wait {remain} min before tapping again."
    return True, ""


def tap_student(
    school_id: int,
    query: str,
    action: str = "auto",
    source: str = "nfc",
    date: str | None = None,
) -> tuple[bool, str, Optional[dict]]:
    student, err = find_student_for_tap(school_id, query)
    if not student:
        return False, err, None
    return mark_attendance(
        school_id, student["id"], action=action, source=source, date=date, notify=True
    )


def mark_attendance(
    school_id: int,
    student_pk: int,
    action: str = "auto",
    source: str = "manual",
    date: str | None = None,
    notify: bool = True,
) -> tuple[bool, str, Optional[dict]]:
    date = date or today_str()
    action = (action or "auto").lower()
    student = get_student(school_id, student_pk)
    if not student:
        return False, "Student not found.", None
    first = student["name"].split()[0]
    now_t = local_time_str()
    pretty = local_time_ampm()
    requested = action
    src = (source or "m")[:8]
    row = _today_att(school_id, student_pk, date)

    if action == "absent":
        payload = {
            "school_id": school_id,
            "student_pk": student_pk,
            "day": date,
            "time_in": None,
            "time_out": None,
            "src": src,
        }
        queued = _persist_attendance(payload, row, notify=None)
        extra = " Saved offline. Will sync when internet returns." if queued else ""
        return True, f"{student['name']} marked absent.{extra}", {
            "student": student,
            "action": "absent",
            "date": date,
            "time": None,
            "is_present": 0,
        }

    if action == "auto":
        if not row or not row.get("time_in"):
            action = "in"
        elif not row.get("time_out"):
            action = "out"
        else:
            return (
                False,
                f"{student['name']} already has in and out for this date.",
                {"student": student, "action": "done", **row},
            )

    if action == "in":
        if requested == "auto" and row and row.get("time_in"):
            ok, msg = _cooldown_ok(date, row.get("time_in"), config.CHECKIN_COOLDOWN_MINUTES)
            if not ok:
                return False, msg, {"student": student, **row}
        payload = {
            "school_id": school_id,
            "student_pk": student_pk,
            "day": date,
            "time_in": now_t,
            "time_out": row.get("time_out") if row else None,
            "src": src,
        }
        title = f"{first} arrived at school"
        body = f"{student['name']} arrived at school at {pretty}."
        note = {"title": title, "body": body, "phone": student["parent_phone"]} if notify else None
        queued = _persist_attendance(payload, row, note)
        if queued:
            body = f"{body} Saved offline. Will sync when internet returns."
        elif notify:
            sent = dispatch_fcm(school_id, student["parent_phone"], title, body, "arrival")
            body = f"{body} Notification sent." if sent else f"{body} Parent app has not registered for push yet."
        return True, body, {
            "student": student,
            "action": "in",
            "date": date,
            "time": now_t,
            "time_display": pretty,
            "is_present": 1,
            "message": body,
        }

    if action == "out":
        if not row or not row.get("time_in"):
            return False, f"{student['name']} has not been marked in yet.", None
        if requested == "auto" and row.get("time_out"):
            ok, msg = _cooldown_ok(date, row.get("time_out"), config.CHECKOUT_COOLDOWN_MINUTES)
            if not ok:
                return False, msg, {"student": student, **row}
        payload = {
            "school_id": school_id,
            "student_pk": student_pk,
            "day": date,
            "time_in": row.get("time_in"),
            "time_out": now_t,
            "src": src,
        }
        title = f"{first} left school"
        body = f"{student['name']} left school at {pretty}."
        note = {"title": title, "body": body, "phone": student["parent_phone"]} if notify else None
        queued = _persist_attendance(payload, row, note)
        if queued:
            body = f"{body} Saved offline. Will sync when internet returns."
        elif notify:
            sent = dispatch_fcm(school_id, student["parent_phone"], title, body, "departure")
            body = f"{body} Notification sent." if sent else f"{body} Parent app has not registered for push yet."
        return True, body, {
            "student": student,
            "action": "out",
            "date": date,
            "time": now_t,
            "time_display": pretty,
            "is_present": 1,
            "message": body,
        }
    return False, "Unknown attendance action.", None


def _persist_attendance(payload: dict, existing: dict | None, notify: dict | None) -> bool:
    """Write to cloud if possible. Otherwise keep locally and queue. Returns True if queued."""
    from app.offline import enqueue_attendance, is_network_error, save_attendance

    try:
        if existing and existing.get("id") and not existing.get("pending"):
            upd(
                "attendance",
                {
                    "time_in": payload.get("time_in"),
                    "time_out": payload.get("time_out"),
                    "src": payload.get("src"),
                },
                id=existing["id"],
            )
        else:
            remote = sel_one(
                "attendance",
                school_id=payload["school_id"],
                student_pk=payload["student_pk"],
                day=payload["day"],
            )
            if remote:
                upd(
                    "attendance",
                    {
                        "time_in": payload.get("time_in"),
                        "time_out": payload.get("time_out"),
                        "src": payload.get("src"),
                    },
                    id=remote["id"],
                )
            else:
                ins(
                    "attendance",
                    {
                        "school_id": payload["school_id"],
                        "student_pk": payload["student_pk"],
                        "day": payload["day"],
                        "time_in": payload.get("time_in"),
                        "time_out": payload.get("time_out"),
                        "src": payload.get("src"),
                    },
                )
        save_attendance(payload, pending=False)
        return False
    except Exception as exc:
        if not is_network_error(exc):
            raise
        save_attendance(payload, pending=True)
        enqueue_attendance(payload, notify)
        return True


def attendance_sheet(school_id: int, date: str | None = None) -> list[dict]:
    from app.offline import is_network_error, local_attendance

    date = date or today_str()
    students = list_students(school_id)
    rows = []
    try:
        rows = sel("attendance", school_id=school_id, day=date)
    except Exception as exc:
        if not is_network_error(exc):
            raise
    by_pk = {r["student_pk"]: r for r in rows}
    for rec in local_attendance(school_id, None, date):
        by_pk[rec["student_pk"]] = rec
    sheet = []
    for s in students:
        rec = by_pk.get(s["id"])
        present = bool(rec and rec.get("time_in"))
        sheet.append(
            {
                **s,
                "date": date,
                "time_in": rec.get("time_in") if rec else None,
                "time_out": rec.get("time_out") if rec else None,
                "time_in_display": format_ampm(rec.get("time_in") if rec else None),
                "time_out_display": format_ampm(rec.get("time_out") if rec else None),
                "is_present": 1 if present else 0,
                "source": rec.get("src") if rec else "",
                "status": "Present" if present else "Absent",
            }
        )
    return sheet


def school_today_stats(school_id: int, date: str | None = None) -> dict[str, Any]:
    date = date or today_str()
    sheet = attendance_sheet(school_id, date)
    present = sum(1 for r in sheet if r["is_present"])
    return {
        "date": date,
        "total": len(sheet),
        "present": present,
        "absent": len(sheet) - present,
        "classes": unique_classes(sheet),
    }


def month_attendance(school_id: int, student_pk: int, year: int, month: int) -> dict[str, Any]:
    start = f"{year:04d}-{month:02d}-01"
    last = calendar.monthrange(year, month)[1]
    end = f"{year:04d}-{month:02d}-{last:02d}"
    student = get_student(school_id, student_pk)
    rows = (
        sb()
        .table("attendance")
        .select("day,time_in,time_out")
        .eq("school_id", school_id)
        .eq("student_pk", student_pk)
        .gte("day", start)
        .lte("day", end)
        .execute()
        .data
        or []
    )
    by_date = {r["day"]: r for r in rows}
    today = today_str()
    days = []
    present_count = 0
    absent_count = 0
    for day in range(1, last + 1):
        date = f"{year:04d}-{month:02d}-{day:02d}"
        rec = by_date.get(date)
        weekday = datetime.strptime(date, "%Y-%m-%d").weekday()
        if rec and rec.get("time_in"):
            status = "present"
            present_count += 1
        elif rec and not rec.get("time_in"):
            status = "absent"
            absent_count += 1
        elif date > today or weekday >= 5:
            status = "none"
        else:
            status = "absent"
            absent_count += 1
        days.append(
            {
                "date": date,
                "day": day,
                "weekday": weekday,
                "status": status,
                "time_in": format_ampm(rec.get("time_in") if rec else None),
                "time_out": format_ampm(rec.get("time_out") if rec else None),
            }
        )
    return {
        "student": student,
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "days": days,
        "present": present_count,
        "absent": absent_count,
        "total_marked": present_count + absent_count,
    }


def recent_taps(school_id: int, limit: int = 12) -> list[dict]:
    date = today_str()
    rows = [
        r
        for r in sel("attendance", school_id=school_id, day=date)
        if r.get("time_in")
    ]
    rows = sorted(rows, key=lambda r: r.get("time_in") or "", reverse=True)[:limit]
    students = {s["id"]: s for s in list_students(school_id)}
    out = []
    for r in rows:
        s = students.get(r["student_pk"], {})
        out.append(
            {
                **r,
                "name": s.get("name", ""),
                "class_name": s.get("class_name", ""),
                "student_id": s.get("student_id", ""),
                "time_in_display": format_ampm(r.get("time_in")),
                "time_out_display": format_ampm(r.get("time_out")),
            }
        )
    return out


def send_school_alert(
    school_id: int, title: str, body: str, template_key: str | None = None
) -> tuple[bool, str, Optional[dict]]:
    title = (title or "").strip()
    body = (body or "").strip()
    if not title or not body:
        return False, "Title and message are required.", None
    from app.offline import enqueue_alert, is_network_error

    try:
        row = ins("alerts", {"school_id": school_id, "title": title, "body": body})
        delivered = dispatch_fcm_school(school_id, title, body, "alert")
        extra = f" Push reached {delivered} device(s)." if delivered else ""
        return True, f"Alert sent.{extra}", row
    except Exception as exc:
        if not is_network_error(exc):
            raise
        enqueue_alert(school_id, title, body)
        return True, "Alert saved offline. It will send when internet returns.", {
            "title": title,
            "body": body,
        }


def list_alerts(school_id: int, limit: int = 40) -> list[dict]:
    return (
        sb()
        .table("alerts")
        .select("*")
        .eq("school_id", school_id)
        .order("id", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )


def children_for_phone(school_id: int, phone: str) -> list[dict]:
    phone = normalize_phone(phone)
    rows = sel("students", school_id=school_id, parent_phone=phone)
    return [_student(r) for r in rows]


def _sign_parent(school_id: int, phone: str, student_pk: int) -> str:
    payload = json.dumps(
        {"s": school_id, "p": phone, "c": student_pk}, separators=(",", ":")
    )
    raw = urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    sig = hmac.new(config.SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()[:24]
    return f"{raw}.{sig}"


def _read_parent(token: str) -> Optional[dict]:
    try:
        raw, sig = token.split(".", 1)
        expect = hmac.new(config.SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()[:24]
        if not hmac.compare_digest(sig, expect):
            return None
        pad = "=" * (-len(raw) % 4)
        data = json.loads(urlsafe_b64decode(raw + pad))
        return {"school_id": data["s"], "parent_phone": data["p"], "selected_student_pk": data["c"]}
    except Exception:
        return None


def parent_login(school_name: str, phone: str, dob: str) -> tuple[bool, str, Optional[dict]]:
    school = find_school_by_name(school_name)
    if not school:
        return False, "School not found. Check the school name.", None
    if not school.get("is_active"):
        return False, "This school is currently inactive.", None
    phone = normalize_phone(phone)
    dob_iso = normalize_dob(dob)
    if len(phone) != 10:
        return False, "Enter the 10-digit parent mobile number.", None
    if not dob_iso:
        return False, "Enter the student's date of birth as DD/MM/YYYY.", None
    children = children_for_phone(school["id"], phone)
    if not children:
        return False, "No student is linked to this mobile number.", None
    matched = [c for c in children if str(c.get("dob"))[:10] == dob_iso]
    if not matched:
        return False, "Date of birth does not match any child on this number.", None
    selected = matched[0]
    token = _sign_parent(school["id"], phone, selected["id"])
    return True, "Signed in.", {
        "token": token,
        "school": {"id": school["id"], "name": school["name"]},
        "children": [_child_public(c) for c in children],
        "selected": _child_public(selected),
    }


def get_parent_session(token: str) -> Optional[dict]:
    sess = _read_parent((token or "").strip())
    if not sess:
        return None
    school = get_school(sess["school_id"])
    if not school:
        return None
    children = children_for_phone(sess["school_id"], sess["parent_phone"])
    selected = next((c for c in children if c["id"] == sess.get("selected_student_pk")), None)
    if not selected and children:
        selected = children[0]
    sess["school"] = school
    sess["children"] = children
    sess["selected"] = selected
    return sess


def switch_parent_child(token: str, student_pk: int) -> tuple[bool, str, Optional[dict]]:
    sess = get_parent_session(token)
    if not sess:
        return False, "Please sign in again.", None
    child = next((c for c in sess["children"] if c["id"] == int(student_pk)), None)
    if not child:
        return False, "That child is not linked to this account.", None
    sess["selected"] = child
    sess["token"] = _sign_parent(sess["school_id"], sess["parent_phone"], child["id"])
    return True, "Switched child.", sess


def delete_parent_session(_token: str) -> None:
    return None


def parent_notifications(
    school_id: int,
    phone: str,
    since_id: int = 0,
    student_pk: int | None = None,
    limit: int = 50,
) -> list[dict]:
    items: list[dict] = []
    for alert in list_alerts(school_id, 20):
        items.append(
            {
                "id": 1_000_000 + int(alert["id"]),
                "ntype": "alert",
                "title": alert["title"],
                "body": alert["body"],
                "created_at": str(alert.get("created_at") or "")[:19].replace("T", " "),
            }
        )
    if student_pk:
        rec = _today_att(school_id, student_pk, today_str())
        student = get_student(school_id, student_pk)
        name = student["name"] if student else "Student"
        if rec and rec.get("time_in"):
            items.append(
                {
                    "id": int(rec["id"]),
                    "ntype": "arrival",
                    "title": f"{name.split()[0]} arrived at school",
                    "body": f"{name} arrived at school at {format_ampm(rec['time_in'])}.",
                    "created_at": f"{rec.get('day') or today_str()} {rec['time_in']}",
                }
            )
        if rec and rec.get("time_out"):
            items.append(
                {
                    "id": 500_000 + int(rec["id"]),
                    "ntype": "departure",
                    "title": f"{name.split()[0]} left school",
                    "body": f"{name} left school at {format_ampm(rec['time_out'])}.",
                    "created_at": f"{rec.get('day') or today_str()} {rec['time_out']}",
                }
            )
    items = [i for i in items if i["id"] > since_id]
    items.sort(key=lambda i: i["id"], reverse=True)
    return items[:limit]


def parent_today(school_id: int, student_pk: int) -> dict[str, Any]:
    student = get_student(school_id, student_pk)
    rec = _today_att(school_id, student_pk, today_str())
    present = bool(rec and rec.get("time_in"))
    return {
        "student": _child_public(student) if student else None,
        "date": today_str(),
        "is_present": present,
        "status": "Present" if present else "Absent",
        "time_in": format_ampm(rec.get("time_in") if rec else None),
        "time_out": format_ampm(rec.get("time_out") if rec else None),
    }


def _child_public(student: dict | None) -> Optional[dict]:
    if not student:
        return None
    return {
        "id": student["id"],
        "student_id": student["student_id"],
        "name": student["name"],
        "class_name": student["class_name"],
        "dob": student.get("dob"),
        "dob_display": student.get("dob_display") or format_dob(student.get("dob")),
    }


def save_fcm_token(school_id: int, phone: str, token: str) -> tuple[bool, str]:
    token = (token or "").strip()
    phone = normalize_phone(phone)
    if not token or len(phone) != 10:
        return False, "Missing FCM token."
    existing = sel_one("fcm_tokens", token=token)
    if existing:
        upd(
            "fcm_tokens",
            {"school_id": school_id, "parent_phone": phone, "updated_at": datetime.now().isoformat()},
            token=token,
        )
    else:
        ins(
            "fcm_tokens",
            {
                "token": token,
                "school_id": school_id,
                "parent_phone": phone,
                "updated_at": datetime.now().isoformat(),
            },
        )
    return True, "Device registered for push."


def fcm_tokens_for_phone(school_id: int, phone: str) -> list[str]:
    return [r["token"] for r in sel("fcm_tokens", school_id=school_id, parent_phone=normalize_phone(phone))]


def fcm_tokens_for_school(school_id: int) -> list[str]:
    return [r["token"] for r in sel("fcm_tokens", school_id=school_id)]


def fcm_device_count(school_id: int | None = None) -> int:
    if school_id is None:
        return count("fcm_tokens")
    return count("fcm_tokens", school_id=school_id)


def delete_fcm_tokens(tokens: list[str]) -> None:
    for token in tokens:
        delete("fcm_tokens", token=token)


def dispatch_fcm(school_id: int, phone: str, title: str, body: str, ntype: str) -> int:
    from app.fcm import send_push

    return send_push(fcm_tokens_for_phone(school_id, phone), title, body, ntype)


def dispatch_fcm_school(school_id: int, title: str, body: str, ntype: str) -> int:
    from app.fcm import send_push

    return send_push(fcm_tokens_for_school(school_id), title, body, ntype)


def search_schools_public(q: str = "") -> list[dict]:
    rows = (
        sb()
        .table("schools")
        .select("id,name")
        .eq("is_active", True)
        .order("name")
        .execute()
        .data
        or []
    )
    q = (q or "").strip().lower()
    if q:
        rows = [s for s in rows if q in s["name"].lower()]
    return rows[:30]
