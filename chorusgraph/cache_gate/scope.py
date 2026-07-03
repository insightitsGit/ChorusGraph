"""Cache scope identifiers — prefix keys by global/tenant/user/session (H21 T2)."""

from __future__ import annotations

from typing import Optional

from chorusgraph.sections.models import CacheScope


def scope_id(
    scope: CacheScope,
    *,
    tenant_id: str = "default",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    if scope == "global":
        return "global"
    if scope == "tenant":
        return f"tenant:{tenant_id}"
    if scope == "user":
        uid = user_id or tenant_id
        return f"user:{uid}"
    if scope == "session":
        sid = session_id or tenant_id
        return f"session:{sid}"
    return "global"


def normalize_exact_query(query: str) -> str:
    return " ".join((query or "").lower().split())


__all__ = ["normalize_exact_query", "scope_id"]
