"""Cache-hit helpers for FC2 — multi-tool result recovery."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from chorusgraph.examples.finance_agent.nodes import _parse_fx_pair


def _pair_key(data: Dict[str, Any]) -> str:
    return f"{data.get('from_currency', '')}/{data.get('to_currency', '')}"


def collect_cached_tool_results(
    runtime: Any,
    message: str,
    primary: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    F5: On cache hit the gate returns one tool_result; recover related FX rows
    seeded in session_tool_cache (e.g. compare USD/EUR + USD/GBP).
    """
    results: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def add(item: Optional[Dict[str, Any]]) -> None:
        if not isinstance(item, dict) or item.get("rate") is None:
            return
        key = _pair_key(item)
        if key in seen:
            return
        seen.add(key)
        results.append(item)

    add(primary)

    upper = (message or "").upper()
    wants_compare = "COMPARE" in upper or ("EUR" in upper and "GBP" in upper)
    pair = _parse_fx_pair(message)

    for key, value in list(getattr(runtime, "session_tool_cache", {}).items()):
        if str(key).startswith("env:"):
            continue
        if isinstance(value, dict) and value.get("rate") is not None:
            add(value)

    if wants_compare and len(results) < 2:
        # Compare queries need both legs — keep whatever session has.
        pass
    elif pair and len(results) == 0 and primary:
        add(primary)

    return results
