"""PrismLang envelope artifact store and publish helpers."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from chorusgraph.transforms.projector import project_from_raw, project_text, raw_from_state


def compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def store_envelope_artifact(store: Dict[str, Any], envelope_id: str, artifact: Dict[str, Any]) -> None:
    store[f"env:{envelope_id}"] = artifact


def resolve_envelope_artifact(store: Dict[str, Any], envelope_id: Optional[str]) -> Dict[str, Any]:
    if not envelope_id:
        return {}
    cached = store.get(f"env:{envelope_id}")
    return dict(cached) if isinstance(cached, dict) else {}


def publish_hop(
    *,
    cache: Any,
    artifact_store: Dict[str, Any],
    hop: str,
    artifact: Dict[str, Any],
    state: Optional[Dict[str, Any]] = None,
    skip_embed: bool = False,
) -> Dict[str, Any]:
    """
    L0 PrismLang handoff — project artifact, store by envelope_id, append sequence.

    Reuses ingress ``raw_embedding_384`` when present (embed-once per turn).
    """
    if cache is None:
        return {}

    raw_arr = raw_from_state(state) if state else None
    if skip_embed and raw_arr is not None:
        _, envelope = project_from_raw(cache, raw_arr)
    else:
        _, envelope = project_text(cache, compact_json(artifact), raw_384=raw_arr)

    store_envelope_artifact(artifact_store, envelope.envelope_id, artifact)

    return {
        "prism_sequence": [envelope],
        "latest_envelope_id": envelope.envelope_id,
        "vector_hops": [
            {
                "hop": hop,
                "vector_dim": len(envelope.vector),
                "envelope_id": envelope.envelope_id,
            }
        ],
    }


def resolve_previous_artifact(
    artifact_store: Dict[str, Any],
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """Load artifact for the latest envelope pointer in state."""
    env_id = state.get("latest_envelope_id")
    return resolve_envelope_artifact(artifact_store, env_id)


__all__ = [
    "compact_json",
    "publish_hop",
    "resolve_envelope_artifact",
    "resolve_previous_artifact",
    "store_envelope_artifact",
]
