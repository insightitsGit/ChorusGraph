"""PrismEnvelope helpers for the core engine."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from prismlang import PrismEnvelope

PrismEnvelopeLike = Dict[str, Any]


def compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def make_envelope(
    *,
    hop: str,
    artifact: Dict[str, Any],
    vector: List[float],
    category_slug: str,
    rule_chain: List[str],
    turn_id: int,
    envelope_id: Optional[str] = None,
) -> PrismEnvelope:
    """Build a PrismLang envelope dict for bus + channel storage."""
    return PrismEnvelope(
        envelope_id=envelope_id or str(uuid4()),
        vector=[float(x) for x in vector],
        agent_id=hop,
        category_slug=category_slug,
        rule_chain=list(rule_chain),
        turn_id=int(turn_id),
    )


def artifact_from_envelope_store(
    store: Dict[str, Any],
    envelope_id: Optional[str],
) -> Dict[str, Any]:
    if not envelope_id:
        return {}
    cached = store.get(f"env:{envelope_id}")
    return dict(cached) if isinstance(cached, dict) else {}


def store_artifact(store: Dict[str, Any], envelope_id: str, artifact: Dict[str, Any]) -> None:
    store[f"env:{envelope_id}"] = artifact


__all__ = [
    "PrismEnvelopeLike",
    "artifact_from_envelope_store",
    "compact_json",
    "make_envelope",
    "store_artifact",
]
