"""Tiny demo seed — only if the Supabase project is empty."""
from __future__ import annotations

from datetime import datetime, timedelta

from app import config
from app.domain import (
    apply_license_to_school,
    create_license_key,
    create_school,
    ensure_super_admin,
    new_nfc_uid,
)
from app.store import configured, count, ins


DEMO = [
    ("C3A01", "Aarav Sharma", "3-A", "9876543210", "2016-04-12", "AT7K2M9Q4X"),
    ("C1B04", "Anaya Sharma", "1-B", "9876543210", "2018-09-03", "AT3P8C1L6D"),
    ("C3A02", "Vihaan Mehta", "3-A", "9811122233", "2016-01-22", None),
    ("C4A01", "Reyansh Patel", "4-A", "9877788899", "2015-02-11", None),
    ("C5A01", "Anika Bose", "5-A", "9823344556", "2014-03-21", None),
    ("C2A01", "Ayaan Gupta", "2-A", "9878899001", "2017-05-07", None),
]


def seed_if_empty() -> None:
    if not configured():
        return
    ensure_super_admin()
    if count("schools") > 0:
        return
    trial = (datetime.now() + timedelta(days=365)).isoformat()
    lic = create_license_key(365, 200, "starter", "system")
    ok, _msg, school = create_school(
        config.DEMO_SCHOOL_NAME,
        config.DEMO_SCHOOL_USER,
        config.DEMO_SCHOOL_PASS,
        license_expires_at=trial,
        max_students=200,
    )
    if not ok or not school:
        return
    apply_license_to_school(school["id"], lic["key_code"])
    for sid, name, klass, phone, dob, nfc in DEMO:
        ins(
            "students",
            {
                "school_id": school["id"],
                "student_id": sid,
                "name": name,
                "class_name": klass,
                "parent_phone": phone,
                "dob": dob,
                "nfc_uid": (nfc or new_nfc_uid()).upper(),
            },
        )
    create_school(
        "Riverdale High",
        "riverdale",
        "School@123",
        license_expires_at=(datetime.now() + timedelta(days=9)).isoformat(),
        max_students=80,
    )
    create_license_key(30, 200, "unused", "system")
