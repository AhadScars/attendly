"""Attendly application configuration."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def private_dir() -> Path:
    """Secrets live here — never inside a folder you zip and send."""
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        path = Path(os.environ["LOCALAPPDATA"]) / "Attendly"
    else:
        path = Path.home() / ".local" / "share" / "attendly"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _parse_env_text(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            out[key] = value
    return out


def _read_env_file(path: Path) -> dict[str, str]:
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        text = data.decode("utf-16")
    else:
        text = data.decode("utf-8-sig")
    return _parse_env_text(text)


def env_file_candidates() -> list[Path]:
    # AppData first so a shared EXE folder never needs .env inside it.
    roots = [private_dir(), app_root()]
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent)
    try:
        roots.append(Path.cwd())
    except OSError:
        pass
    names = (".env", "attendly.env")
    seen: set[str] = set()
    paths: list[Path] = []
    for root in roots:
        for name in names:
            path = root / name
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)
    return paths


LOADED_ENV_FILE = ""


def load_env() -> None:
    global LOADED_ENV_FILE
    for path in env_file_candidates():
        try:
            if not path.is_file():
                continue
            values = _read_env_file(path)
            if not values:
                continue
            for key, value in values.items():
                os.environ.setdefault(key, value)
            LOADED_ENV_FILE = str(path)
            return
        except OSError:
            continue


load_env()


def client_config_path() -> Path:
    return private_dir() / "client.json"


def remote_server_url() -> str:
    path = client_config_path()
    if not path.is_file():
        return ""
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        return str(data.get("remote") or "").strip().rstrip("/")
    except Exception:
        return ""


def save_remote_server(url: str) -> None:
    import json

    path = client_config_path()
    path.write_text(json.dumps({"remote": url.strip().rstrip("/")}), encoding="utf-8")


def save_owner_env(url: str, service_key: str, secret: str = "") -> Path:
    dest = private_dir() / ".env"
    lines = [
        f"SUPABASE_URL={url.strip()}",
        f"SUPABASE_SERVICE_KEY={service_key.strip()}",
        f"ATTENDLY_SECRET={(secret or os.environ.get('ATTENDLY_SECRET') or 'attendly-change-me-before-production').strip()}",
        "",
    ]
    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest


ROOT = app_root()
EXPORTS_DIR = ROOT / "exports"
TIMEZONE = os.environ.get("ATTENDLY_TZ", "").strip()


def resolve_fcm_credentials() -> Path:
    env = os.environ.get("ATTENDLY_FCM_CREDENTIALS")
    candidates = []
    if env:
        candidates.append(Path(env))
    priv = private_dir()
    candidates.extend(
        [
            priv / "firebase" / "firebase-adminsdk.json",
            priv / "firebase-adminsdk.json",
            ROOT / "data" / "firebase-adminsdk.json",
            ROOT / "firebase" / "firebase-adminsdk.json",
            ROOT / "firebase-adminsdk.json",
            Path(sys.executable).resolve().parent / "data" / "firebase-adminsdk.json",
            Path(sys.executable).resolve().parent / "firebase" / "firebase-adminsdk.json",
            Path(sys.executable).resolve().parent / "firebase-adminsdk.json",
        ]
    )
    for path in candidates:
        try:
            if path.is_file() and path.stat().st_size > 20:
                return path
        except OSError:
            continue
    return candidates[0]


FCM_CREDENTIALS = resolve_fcm_credentials()
SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").strip()
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY") or ""
).strip()

SECRET_KEY = os.environ.get("ATTENDLY_SECRET", "attendly-change-me-before-production")

SUPER_ADMIN_USER = os.environ.get("ATTENDLY_OWNER_USER", "owner")
SUPER_ADMIN_PASS = os.environ.get("ATTENDLY_OWNER_PASS", "Attendly@2026")
SUPER_ADMIN_NAME = "Attendly Owner"

DEMO_SCHOOL_NAME = "Green Spring Public School"
DEMO_SCHOOL_USER = "greenspring"
DEMO_SCHOOL_PASS = "School@123"

HOST = os.environ.get("ATTENDLY_HOST", "0.0.0.0")
PORT = int(os.environ.get("ATTENDLY_PORT", "5055"))

DEFAULT_CLASS_NUMS = [str(i) for i in range(1, 13)]
DEFAULT_SECTIONS = ["A", "B", "C", "D"]

CHECKIN_COOLDOWN_MINUTES = int(os.environ.get("ATTENDLY_CHECKIN_COOLDOWN", "20"))
CHECKOUT_COOLDOWN_MINUTES = int(os.environ.get("ATTENDLY_CHECKOUT_COOLDOWN", "20"))

TRIAL_DAYS = 7
DEFAULT_PAGE_SIZE = 15

ALERT_TEMPLATES = [
    {
        "key": "rain_holiday",
        "title": "Holiday — heavy rain",
        "body": "Today is a holiday due to heavy rain. Please keep children home and stay safe.",
    },
    {
        "key": "closed_tomorrow",
        "title": "School closed tomorrow",
        "body": "School will remain closed tomorrow. Regular classes will resume the following working day.",
    },
    {
        "key": "half_day",
        "title": "Half day today",
        "body": "School will function as a half day today. Students will be released at 12:00 PM.",
    },
    {
        "key": "ptm",
        "title": "Parent-teacher meeting",
        "body": "A parent-teacher meeting is scheduled this Saturday from 9:00 AM to 12:00 PM. Your presence is requested.",
    },
    {
        "key": "winter_uniform",
        "title": "Winter uniform",
        "body": "Please send your child in the complete winter uniform from tomorrow.",
    },
    {
        "key": "sports_postponed",
        "title": "Sports day postponed",
        "body": "Sports day has been postponed. A new date will be shared shortly.",
    },
    {
        "key": "bus_late",
        "title": "School bus running late",
        "body": "School buses are running late today due to traffic. Please wait at the stop.",
    },
    {
        "key": "exams_start",
        "title": "Examinations begin Monday",
        "body": "Examinations start from Monday. Please ensure your child arrives on time with the required stationery.",
    },
    {
        "key": "fee_reminder",
        "title": "Fee payment reminder",
        "body": "This is a reminder to complete fee payment by the end of this month.",
    },
    {
        "key": "annual_rehearsal",
        "title": "Annual day rehearsal",
        "body": "Annual day rehearsal will be held after school today. Students may reach home later than usual.",
    },
    {
        "key": "early_close_weather",
        "title": "Early closing — weather",
        "body": "School will close early today due to weather conditions. Please arrange pickup accordingly.",
    },
    {
        "key": "vaccination",
        "title": "Vaccination camp",
        "body": "A vaccination camp will be held on campus tomorrow. Consent forms, if any, should be submitted at the gate.",
    },
    {
        "key": "picnic",
        "title": "Picnic reminder",
        "body": "Please send a water bottle, cap, and a light snack with your child for the picnic.",
    },
    {
        "key": "junior_cancelled",
        "title": "Classes cancelled — Grades 1 to 3",
        "body": "Classes for Grades 1 to 3 are cancelled today. Senior classes will continue as scheduled.",
    },
    {
        "key": "result_day",
        "title": "Result day",
        "body": "Result day is on Friday. Parents are invited to collect report cards from the school office.",
    },
    {
        "key": "report_cards",
        "title": "Collect report cards",
        "body": "Please collect report cards from the school office during working hours.",
    },
    {
        "key": "extra_class",
        "title": "Extra class tomorrow",
        "body": "An extra class will be held tomorrow at 8:00 AM. Please ensure your child reaches school on time.",
    },
    {
        "key": "open_as_usual",
        "title": "School open as usual",
        "body": "School remains open as usual today. Regular timings apply.",
    },
    {
        "key": "lost_and_found",
        "title": "Lost and found",
        "body": "Several items are waiting in lost and found. Please check with the school office.",
    },
    {
        "key": "emergency_pickup",
        "title": "Emergency pickup",
        "body": "Emergency: please pick up your child from school as soon as possible and contact the office.",
    },
]
