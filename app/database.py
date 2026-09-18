"""Time helpers only. All data lives in Supabase — no local SQLite."""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from app import config

_win_delta: timedelta | None = None
_win_checked = False


def _is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def _windows_clock_delta() -> timedelta | None:
    """WSL is often UTC; the school PC clock is what staff see."""
    try:
        raw = subprocess.check_output(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "[DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss')",
            ],
            timeout=3,
            stderr=subprocess.DEVNULL,
        )
        win = datetime.strptime(raw.decode().strip().splitlines()[-1].strip(), "%Y-%m-%d %H:%M:%S")
        return win - datetime.now()
    except Exception:
        return None


def naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def local_now() -> datetime:
    """School computer local time. Optional ATTENDLY_TZ override, else PC clock."""
    override = (getattr(config, "TIMEZONE", "") or "").strip()
    if override:
        try:
            from zoneinfo import ZoneInfo

            return naive(datetime.now(ZoneInfo(override))) or datetime.now()
        except Exception:
            pass
    global _win_delta, _win_checked
    now = datetime.now()
    if _is_wsl():
        if not _win_checked:
            _win_delta = _windows_clock_delta()
            _win_checked = True
        if _win_delta is not None:
            return now + _win_delta
    return now


def now_iso() -> str:
    return local_now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return local_now().strftime("%Y-%m-%d")


def local_time_str() -> str:
    return local_now().strftime("%H:%M:%S")


def local_time_ampm() -> str:
    return local_now().strftime("%I:%M %p").lstrip("0")


def format_ampm(time_str: str | None) -> str:
    if not time_str:
        return ""
    time_str = time_str.strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(time_str, fmt).strftime("%I:%M %p").lstrip("0")
        except ValueError:
            continue
    return time_str


def combine_local(date_str: str, time_str: str) -> datetime | None:
    if not date_str or not time_str:
        return None
    time_str = time_str.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(f"{date_str} {time_str}", fmt)
        except ValueError:
            continue
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(f"{date_str} {time_str}", f"%Y-%m-%d {fmt}")
        except ValueError:
            continue
    return None


def row_to_dict(row: Optional[Any]) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows: list[Any]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]
