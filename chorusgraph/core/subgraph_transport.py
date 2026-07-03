"""Remote subgraph transport contract — Improve-1 T5."""

from __future__ import annotations

from typing import Any, Dict, Optional

from chorusgraph.core.envelope import compact_json
from chorusgraph.core.subgraph import SubgraphSpec
from chorusgraph.transport.chorus import ChorusSpine
from chorusgraph.transport.prismapi import PrismAPISpine


def encode_boundary_envelope(child_input: Dict[str, Any]) -> Dict[str, Any]:
    vector = list(child_input.get("vector") or [0.0] * 64)
    return {
        "envelope_id": str(child_input.get("envelope_id") or "boundary"),
        "vector_64": vector,
        "artifact_ref": compact_json({k: v for k, v in child_input.items() if k != "vector"}),
        "hop": "subgraph_boundary",
    }


def decode_boundary_envelope(frame: Dict[str, Any]) -> Dict[str, Any]:
    import json

    payload = frame.get("artifact_ref") or "{}"
    try:
        data = json.loads(payload) if isinstance(payload, str) else dict(payload)
    except json.JSONDecodeError:
        data = {"raw_output": str(payload)}
    data["vector"] = list(frame.get("vector_64") or [0.0] * 64)
    data["envelope_id"] = frame.get("envelope_id")
    return data


def invoke_remote_subgraph(
    spec: SubgraphSpec,
    child_input: Dict[str, Any],
    *,
    config: Dict[str, Any],
    parent_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Encode → route → decode round-trip (in-memory contract; no network)."""
    encoded = encode_boundary_envelope(child_input)
    if spec.location == "chorus":
        spine = ChorusSpine(tenant_id=str(config.get("configurable", {}).get("tenant_id") or "default"))
        frame = spine.encode_frame(
            envelope_id=str(encoded["envelope_id"]),
            vector_64=list(encoded["vector_64"]),
            hop=str(encoded["hop"]),
            artifact_ref=str(encoded["artifact_ref"]),
            metadata={"subgraph": spec.name, "parent_run_id": parent_run_id},
        )
        spine.deliver(frame, from_hop="parent", to_hop=spec.name)
        routed = {
            "envelope_id": frame.envelope_id,
            "vector_64": frame.vector_64,
            "artifact_ref": frame.artifact_ref,
        }
    elif spec.location == "prismapi":
        spine = PrismAPISpine(tenant_id=str(config.get("configurable", {}).get("tenant_id") or "default"))
        routed = spine.route_envelope(encoded)
    else:
        raise ValueError(f"Unsupported remote subgraph location: {spec.location!r}")

    decoded = decode_boundary_envelope(routed)
    return spec.child.invoke(
        decoded,
        config=config,
        _parent_run_id=parent_run_id,
        _subgraph_node=spec.name,
    )


__all__ = ["decode_boundary_envelope", "encode_boundary_envelope", "invoke_remote_subgraph"]
