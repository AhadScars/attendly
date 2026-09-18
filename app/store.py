"""Supabase access. Service-role key stays on the school/owner process only."""
from __future__ import annotations

from typing import Any

from app import config

_client = None


def configured() -> bool:
    return bool(config.SUPABASE_URL and config.SUPABASE_KEY)


def sb():
    global _client
    if _client is None:
        if not configured():
            raise RuntimeError(
                "Supabase is not configured. Add SUPABASE_URL and SUPABASE_SERVICE_KEY to .env"
            )
        from supabase import create_client

        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


def sel(table: str, columns: str = "*", **eq: Any) -> list[dict]:
    q = sb().table(table).select(columns)
    for key, value in eq.items():
        q = q.eq(key, value)
    return q.execute().data or []


def sel_one(table: str, columns: str = "*", **eq: Any) -> dict | None:
    rows = sel(table, columns, **eq)
    return rows[0] if rows else None


def ins(table: str, row: dict) -> dict:
    data = sb().table(table).insert(row).execute().data or []
    if not data:
        raise RuntimeError(f"Insert into {table} returned no row.")
    return data[0]


def upd(table: str, row: dict, **eq: Any) -> dict | None:
    q = sb().table(table).update(row)
    for key, value in eq.items():
        q = q.eq(key, value)
    data = q.execute().data or []
    return data[0] if data else None


def delete(table: str, **eq: Any) -> None:
    q = sb().table(table).delete()
    for key, value in eq.items():
        q = q.eq(key, value)
    q.execute()


def count(table: str, **eq: Any) -> int:
    q = sb().table(table).select("*", count="exact")
    for key, value in eq.items():
        q = q.eq(key, value)
    result = q.limit(1).execute()
    return int(result.count or 0)
