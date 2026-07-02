"""Container F — envelope artifacts for finance multi-agent handoffs."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def store_envelope_artifact(runtime: Any, envelope_id: str, artifact: Dict[str, Any]) -> None:
    runtime.session_tool_cache[f"env:{envelope_id}"] = artifact


def resolve_envelope_artifact(runtime: Any, envelope_id: Optional[str]) -> Dict[str, Any]:
    if not envelope_id:
        return {}
    cached = runtime.session_tool_cache.get(f"env:{envelope_id}")
    return dict(cached) if isinstance(cached, dict) else {}


def envelope_handoff(
    *,
    hop: str,
    envelope_id: Optional[str],
    hop_input: Optional[Dict[str, Any]] = None,
) -> str:
    payload: Dict[str, Any] = {"hop": hop, "previous_envelope_id": envelope_id}
    if hop_input:
        payload["hop_input"] = hop_input
    return compact_json(payload)


def compact_plan(artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not artifact:
        return {}
    tools = artifact.get("tools") or []
    slim_tools: List[Dict[str, Any]] = []
    for t in list(tools)[:4]:
        if isinstance(t, dict):
            slim_tools.append({"tool": t.get("tool"), "args": t.get("args") or {}})
    return {
        "plan": str(artifact.get("plan") or "")[:180],
        "tools": slim_tools,
    }


def compact_tool(artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not artifact:
        return {}
    results = list(artifact.get("results") or [])[:4]
    return {
        "primary": artifact.get("primary") or {},
        "n_calls": int(artifact.get("n_calls") or 0),
        "results": results,
    }


def compact_draft(artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not artifact:
        return {}
    return {"excerpt": str(artifact.get("draft") or "")[:200]}
