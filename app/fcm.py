"""Firebase Cloud Messaging sender. No-op until a service-account file is present."""
from __future__ import annotations

import logging
from typing import Iterable

from app import config

log = logging.getLogger("attendly.fcm")

_ready: bool | None = None


def credentials_path():
    return config.FCM_CREDENTIALS


def is_configured() -> bool:
    path = credentials_path()
    try:
        return path.is_file() and path.stat().st_size > 20
    except OSError:
        return False


def init_firebase() -> bool:
    global _ready
    if _ready is not None:
        return _ready
    if not is_configured():
        _ready = False
        return False
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(str(credentials_path())))
        _ready = True
        return True
    except Exception as exc:
        log.warning("Firebase init failed: %s", exc)
        _ready = False
        return False


def send_push(tokens: Iterable[str], title: str, body: str, ntype: str = "alert") -> int:
    """Send a high-priority FCM notification. Returns how many devices accepted it."""
    uniq = [t.strip() for t in tokens if t and t.strip()]
    if not uniq:
        return 0
    if not init_firebase():
        return 0

    from firebase_admin import messaging

    sent = 0
    dead: list[str] = []
    for start in range(0, len(uniq), 500):
        batch = uniq[start : start + 500]
        message = messaging.MulticastMessage(
            tokens=batch,
            notification=messaging.Notification(title=title, body=body),
            data={"ntype": ntype, "title": title, "body": body},
            android=messaging.AndroidConfig(priority="high"),
        )
        try:
            if hasattr(messaging, "send_each_for_multicast"):
                result = messaging.send_each_for_multicast(message)
            else:
                result = messaging.send_multicast(message)
        except Exception as exc:
            log.warning("FCM send failed: %s", exc)
            continue
        for token, resp in zip(batch, result.responses):
            if resp.success:
                sent += 1
                continue
            err = str(getattr(resp, "exception", "") or "")
            if any(
                mark in err
                for mark in (
                    "Unregistered",
                    "Requested entity was not found",
                    "registration-token-not-registered",
                    "invalid-registration-token",
                )
            ):
                dead.append(token)
    if dead:
        from app.domain import delete_fcm_tokens

        delete_fcm_tokens(dead)
    return sent
