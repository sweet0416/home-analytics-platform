from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from hashlib import sha256
from typing import Protocol


class NavItem(Protocol):
    fund_code: str
    nav_date: date | None
    unit_nav: object
    status: str


def build_nav_fingerprint(items: Iterable[NavItem]) -> tuple[date | None, str]:
    """Build a stable fingerprint from the synced portfolio NAV state."""
    normalized: list[dict[str, str | None]] = []
    nav_dates: list[date] = []
    for item in items:
        if item.status != "succeeded" or item.nav_date is None:
            continue
        nav_dates.append(item.nav_date)
        normalized.append(
            {
                "fund_code": item.fund_code,
                "nav_date": item.nav_date.isoformat(),
                "unit_nav": str(item.unit_nav) if item.unit_nav is not None else None,
            }
        )
    normalized.sort(key=lambda value: (value["fund_code"], value["nav_date"] or ""))
    payload = json.dumps(normalized, ensure_ascii=True, separators=(",", ":"))
    return (max(nav_dates) if nav_dates else None, sha256(payload.encode("utf-8")).hexdigest())
