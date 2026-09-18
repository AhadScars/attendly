#!/usr/bin/env python3
"""Attendly — school + owner desktop entry (dev and PyInstaller EXE)."""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser

if getattr(sys, "frozen", False):
    BASE = os.path.dirname(sys.executable)
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from app import config  # noqa: E402
from app import create_app  # noqa: E402


def open_browser(url: str, delay: float = 1.1) -> None:
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open, daemon=True).start()


def lan_url() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return f"http://{ip}:{config.PORT}"
    except Exception:
        return f"http://<this-pc-ip>:{config.PORT}"


def main() -> None:
    remote = config.remote_server_url()
    if remote:
        print("School client mode — opening", remote)
        print("No keys on this PC.")
        webbrowser.open(remote)
        input("Press Enter to close...")
        return

    app = create_app()
    local = f"http://127.0.0.1:{config.PORT}"
    print("=" * 56)
    print("  Attendly")
    print(f"  School / owner console : {local}")
    print(f"  Parent app server      : {lan_url()}")
    print("  Real phone types this : http://192.168.1.8:5055")
    print("  (10.0.2.2 is emulator only. Same Wi-Fi. Run open-phone-access.bat if blocked.)")
    print("  Owner  : owner / Attendly@2026")
    print("  School : greenspring / School@123")
    print("  Parent : Green Spring Public School")
    print("           phone 9876543210   DOB 12/04/2016")
    print(f"  Env file              : {config.LOADED_ENV_FILE or '(none found next to EXE)'}")
    print(f"  Database              : Supabase {config.SUPABASE_URL or '(not configured)'}")
    print("  Press Ctrl+C to stop")
    print("=" * 56)

    if getattr(sys, "frozen", False) or os.environ.get("ATTENDLY_OPEN", "1") == "1":
        open_browser(local)

    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Attendly failed to start:")
        print(exc)
        import traceback

        traceback.print_exc()
        input("Press Enter to close...")
        raise
