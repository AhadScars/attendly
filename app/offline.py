"""Local queue + cache. Used only when the cloud is unreachable."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import threading
import time
from pathlib import Path

_LOCK = threading.RLock()
_FLUSHING = False


def _dir() -> Path:
    env = os.environ.get("ATTENDLY_QUEUE_DIR")
    if env:
        path = Path(env)
    elif sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        path = Path(os.environ["LOCALAPPDATA"]) / "Attendly"
    else:
        path = Path.home() / ".local" / "share" / "attendly"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_dir() / "queue.db"), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS students (
            school_id INTEGER NOT NULL,
            id INTEGER NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY (school_id, id)
        );
        CREATE TABLE IF NOT EXISTS attendance (
            school_id INTEGER NOT NULL,
            student_pk INTEGER NOT NULL,
            day TEXT NOT NULL,
            time_in TEXT,
            time_out TEXT,
            src TEXT,
            pending INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (school_id, student_pk, day)
        );
        CREATE TABLE IF NOT EXISTS outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            dedupe TEXT UNIQUE NOT NULL,
            payload TEXT NOT NULL,
            notify INTEGER NOT NULL DEFAULT 0,
            notify_title TEXT,
            notify_body TEXT,
            parent_phone TEXT,
            created_at TEXT NOT NULL,
            tries INTEGER NOT NULL DEFAULT 0,
            last_error TEXT
        );
        """
    )
    return conn


def is_network_error(exc: BaseException) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    marks = (
        "timeout",
        "timed out",
        "connection",
        "network",
        "unreachable",
        "nameresolution",
        "failed to",
        "temporarily",
        "ssl",
        "httpx",
        "connect",
        "offline",
        "apierror",
        "503",
        "502",
        "504",
    )
    return any(m in text for m in marks)


def cache_students(school_id: int, students: list[dict]) -> None:
    with _LOCK:
        conn = _db()
        try:
            conn.execute("DELETE FROM students WHERE school_id = ?", (school_id,))
            conn.executemany(
                "INSERT INTO students(school_id, id, payload) VALUES (?,?,?)",
                [(school_id, int(s["id"]), json.dumps(s)) for s in students if s.get("id")],
            )
            conn.commit()
        finally:
            conn.close()


def cached_students(school_id: int) -> list[dict]:
    with _LOCK:
        conn = _db()
        try:
            rows = conn.execute(
                "SELECT payload FROM students WHERE school_id = ?", (school_id,)
            ).fetchall()
        finally:
            conn.close()
    return [json.loads(r["payload"]) for r in rows]


def cached_student(school_id: int, pk: int) -> dict | None:
    with _LOCK:
        conn = _db()
        try:
            row = conn.execute(
                "SELECT payload FROM students WHERE school_id = ? AND id = ?",
                (school_id, pk),
            ).fetchone()
        finally:
            conn.close()
    return json.loads(row["payload"]) if row else None


def save_attendance(row: dict, pending: bool) -> None:
    with _LOCK:
        conn = _db()
        try:
            conn.execute(
                """
                INSERT INTO attendance(school_id, student_pk, day, time_in, time_out, src, pending)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(school_id, student_pk, day) DO UPDATE SET
                    time_in=excluded.time_in,
                    time_out=excluded.time_out,
                    src=excluded.src,
                    pending=excluded.pending
                """,
                (
                    int(row["school_id"]),
                    int(row["student_pk"]),
                    row["day"],
                    row.get("time_in"),
                    row.get("time_out"),
                    row.get("src") or "m",
                    1 if pending else 0,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def local_attendance(school_id: int, student_pk: int | None, day: str) -> list[dict]:
    with _LOCK:
        conn = _db()
        try:
            if student_pk is None:
                rows = conn.execute(
                    "SELECT * FROM attendance WHERE school_id = ? AND day = ?",
                    (school_id, day),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM attendance
                    WHERE school_id = ? AND student_pk = ? AND day = ?
                    """,
                    (school_id, student_pk, day),
                ).fetchall()
        finally:
            conn.close()
    return [dict(r) for r in rows]


def enqueue_attendance(row: dict, notify: dict | None) -> None:
    dedupe = f"att:{row['school_id']}:{row['student_pk']}:{row['day']}"
    payload = json.dumps(row)
    with _LOCK:
        conn = _db()
        try:
            conn.execute(
                """
                INSERT INTO outbox(kind, dedupe, payload, notify, notify_title, notify_body,
                    parent_phone, created_at)
                VALUES ('attendance', ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(dedupe) DO UPDATE SET
                    payload=excluded.payload,
                    notify=excluded.notify,
                    notify_title=excluded.notify_title,
                    notify_body=excluded.notify_body,
                    parent_phone=excluded.parent_phone,
                    last_error=NULL
                """,
                (
                    dedupe,
                    payload,
                    1 if notify else 0,
                    (notify or {}).get("title"),
                    (notify or {}).get("body"),
                    (notify or {}).get("phone"),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def enqueue_alert(school_id: int, title: str, body: str) -> None:
    dedupe = f"alert:{school_id}:{int(time.time() * 1000)}"
    with _LOCK:
        conn = _db()
        try:
            conn.execute(
                """
                INSERT INTO outbox(kind, dedupe, payload, notify, notify_title, notify_body,
                    created_at)
                VALUES ('alert', ?, ?, 1, ?, ?, datetime('now'))
                """,
                (dedupe, json.dumps({"school_id": school_id, "title": title, "body": body}), title, body),
            )
            conn.commit()
        finally:
            conn.close()


def pending_count(school_id: int | None = None) -> int:
    with _LOCK:
        conn = _db()
        try:
            if school_id is None:
                return conn.execute("SELECT COUNT(*) AS c FROM outbox").fetchone()["c"]
            rows = conn.execute("SELECT payload FROM outbox").fetchall()
        finally:
            conn.close()
    n = 0
    for row in rows:
        try:
            if json.loads(row["payload"]).get("school_id") == school_id:
                n += 1
        except Exception:
            n += 1
    return n


_CLOUD = {"ok": None, "at": 0.0}


def cloud_up() -> bool:
    now = time.time()
    if _CLOUD["ok"] is not None and now - _CLOUD["at"] < 5:
        return bool(_CLOUD["ok"])
    try:
        from app.store import sb

        sb().table("schools").select("id").limit(1).execute()
        _CLOUD["ok"] = True
    except Exception:
        _CLOUD["ok"] = False
    _CLOUD["at"] = now
    return bool(_CLOUD["ok"])


def flush_once() -> int:
    global _FLUSHING
    if _FLUSHING:
        return 0
    _FLUSHING = True
    sent = 0
    try:
        from app.store import ins, sel_one, upd

        with _LOCK:
            conn = _db()
            try:
                items = [dict(r) for r in conn.execute("SELECT * FROM outbox ORDER BY id").fetchall()]
            finally:
                conn.close()
        for item in items:
            try:
                payload = json.loads(item["payload"])
                if item["kind"] == "attendance":
                    existing = sel_one(
                        "attendance",
                        school_id=payload["school_id"],
                        student_pk=payload["student_pk"],
                        day=payload["day"],
                    )
                    fields = {
                        "time_in": payload.get("time_in"),
                        "time_out": payload.get("time_out"),
                        "src": payload.get("src") or "m",
                    }
                    if existing:
                        upd("attendance", fields, id=existing["id"])
                    else:
                        ins(
                            "attendance",
                            {
                                "school_id": payload["school_id"],
                                "student_pk": payload["student_pk"],
                                "day": payload["day"],
                                **fields,
                            },
                        )
                    save_attendance(payload, pending=False)
                    if item.get("notify") and item.get("parent_phone"):
                        from app.domain import dispatch_fcm

                        dispatch_fcm(
                            payload["school_id"],
                            item["parent_phone"],
                            item.get("notify_title") or "Attendly",
                            item.get("notify_body") or "",
                            "arrival" if payload.get("time_out") is None else "departure",
                        )
                elif item["kind"] == "alert":
                    from app.domain import dispatch_fcm_school

                    ins(
                        "alerts",
                        {
                            "school_id": payload["school_id"],
                            "title": payload["title"],
                            "body": payload["body"],
                        },
                    )
                    dispatch_fcm_school(payload["school_id"], payload["title"], payload["body"], "alert")
                with _LOCK:
                    conn = _db()
                    try:
                        conn.execute("DELETE FROM outbox WHERE id = ?", (item["id"],))
                        conn.commit()
                    finally:
                        conn.close()
                sent += 1
            except Exception as exc:
                with _LOCK:
                    conn = _db()
                    try:
                        conn.execute(
                            "UPDATE outbox SET tries = tries + 1, last_error = ? WHERE id = ?",
                            (str(exc)[:300], item["id"]),
                        )
                        conn.commit()
                    finally:
                        conn.close()
                if not is_network_error(exc):
                    continue
                break
    finally:
        _FLUSHING = False
    return sent


def start_flusher() -> None:
    def loop():
        while True:
            time.sleep(8)
            try:
                if pending_count() and cloud_up():
                    flush_once()
            except Exception:
                pass

    threading.Thread(target=loop, daemon=True, name="attendly-sync").start()
