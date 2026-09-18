"""Sort helpers for class + section (1-A, 2-B, Class 8-D)."""
from __future__ import annotations

import re
from typing import Any

_CLASS_RE = re.compile(r"(?:class\s*)?(\d+)\s*[-–]?\s*([A-Za-z])?", re.IGNORECASE)


def parse_class_section(class_name: str) -> tuple[int, str, str]:
    raw = (class_name or "").strip()
    m = _CLASS_RE.match(raw)
    if not m:
        return (9999, "", raw.lower())
    num = int(m.group(1))
    section = (m.group(2) or "").upper()
    return (num, section, raw.lower())


def class_sort_key(item: Any) -> tuple:
    if isinstance(item, dict):
        cls = item.get("class_name") or ""
        name = (item.get("name") or "").lower()
        sid = (item.get("student_id") or "").lower()
        num, sec, raw = parse_class_section(cls)
        return (num, sec, raw, name, sid)
    num, sec, raw = parse_class_section(str(item))
    return (num, sec, raw)


def sort_students(students: list[dict]) -> list[dict]:
    return sorted(students, key=class_sort_key)


def filter_students(
    students: list[dict],
    *,
    class_num: str | None = None,
    section: str | None = None,
    class_name: str | None = None,
    q: str | None = None,
) -> list[dict]:
    class_num = (class_num or "").strip()
    section = (section or "").strip().upper()
    class_name = (class_name or "").strip()
    q = (q or "").strip().lower()

    out: list[dict] = []
    for s in students:
        cls = s.get("class_name") or ""
        num, sec, _ = parse_class_section(cls)
        if class_name and cls != class_name:
            continue
        if class_num:
            try:
                if num != int(class_num):
                    continue
            except ValueError:
                continue
        if section and sec != section:
            continue
        if q:
            hay = " ".join(
                [
                    str(s.get("student_id", "")),
                    str(s.get("name", "")),
                    cls,
                    str(s.get("parent_phone", "")),
                    str(s.get("nfc_uid", "")),
                ]
            ).lower()
            if q not in hay:
                continue
        out.append(s)
    return out


def unique_classes(students: list[dict]) -> list[str]:
    labels = {s.get("class_name") or "" for s in students if s.get("class_name")}
    return sorted(labels, key=class_sort_key)
