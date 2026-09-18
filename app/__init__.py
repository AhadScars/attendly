"""Attendly — NFC school attendance on Supabase."""
from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask, request

from app import config
from app.seed import seed_if_empty
from app.store import configured


def _resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "app"
    return Path(__file__).resolve().parent


def create_app() -> Flask:
    root = _resource_root()
    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    app.secret_key = config.SECRET_KEY
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    from app.routes.auth_routes import bp as auth_bp
    from app.routes.parent_api import bp as parent_bp
    from app.routes.school import bp as school_bp
    from app.routes.superadmin import bp as super_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(super_bp)
    app.register_blueprint(school_bp)
    app.register_blueprint(parent_bp)

    @app.after_request
    def add_cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return resp

    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            return ("", 204)
        # Login can still open; school pages use the local queue if the cloud drops later.
        if not configured() and request.endpoint not in {"static"}:
            return (
                "<!doctype html><title>Attendly</title>"
                "<body style='font-family:Segoe UI,sans-serif;padding:40px;max-width:640px'>"
                "<h2>Connect Supabase</h2>"
                "<p>Put <code>SUPABASE_URL</code> and <code>SUPABASE_SERVICE_KEY</code> "
                "in a <code>.env</code> file next to Attendly, then restart.</p>"
                "<p>SQL: <code>supabase/schema.sql</code></p></body>",
                503,
            )

    @app.context_processor
    def queue_status():
        from app.offline import cloud_up, pending_count

        sid = None
        try:
            from flask import session

            sid = session.get("school_id")
        except Exception:
            sid = None
        try:
            pending = pending_count(sid)
            online = cloud_up()
        except Exception:
            pending = 0
            online = False
        return {"queue_pending": pending, "queue_online": online}

    if configured():
        seed_if_empty()
        from app.offline import start_flusher

        start_flusher()
    return app
