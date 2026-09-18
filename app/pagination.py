"""List pagination helpers."""
from __future__ import annotations

from typing import Any


DEFAULT_PER_PAGE = 15


def query_args(**kwargs) -> dict:
    out = {}
    for k, v in kwargs.items():
        if v is None or v == "" or v is False:
            continue
        out[k] = v
    return out


def parse_page(raw: str | None, default: int = 1) -> int:
    try:
        p = int(raw or default)
        return p if p >= 1 else 1
    except (TypeError, ValueError):
        return 1


def parse_per_page(raw: str | None, default: int = DEFAULT_PER_PAGE) -> int:
    try:
        n = int(raw or default)
        return min(100, max(10, n))
    except (TypeError, ValueError):
        return default


def paginate(items: list[Any], page: int = 1, per_page: int = DEFAULT_PER_PAGE) -> dict[str, Any]:
    total = len(items)
    pages = max(1, (total + per_page - 1) // per_page) if total else 1
    page = max(1, min(int(page or 1), pages))
    start = (page - 1) * per_page
    end = start + per_page
    page_items = items[start:end]

    window = 2
    page_numbers: list[int | None] = []
    for p in range(1, pages + 1):
        if p == 1 or p == pages or abs(p - page) <= window:
            if page_numbers and page_numbers[-1] is not None and p - page_numbers[-1] > 1:
                page_numbers.append(None)
            page_numbers.append(p)

    return {
        "rows": page_items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_page": page - 1,
        "next_page": page + 1,
        "start_index": (start + 1) if total else 0,
        "end_index": min(end, total),
        "page_numbers": page_numbers,
    }
