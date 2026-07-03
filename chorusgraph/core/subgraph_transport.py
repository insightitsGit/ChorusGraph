"""Remote subgraph transport — boundary encode/decode + batch Send-over-transport."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from chorusgraph.core.envelope import compact_json
from chorusgraph.core.subgraph import SubgraphSpec
from chorusgraph.transport.chorus import (
    ChorusBatchFrame,
    ChorusFrame,
    ChorusSpine,
    encode_batch_frame,
)
from chorusgraph.transport.prismapi import PrismAPISpine

if TYPE_CHECKING:
    from chorusgraph.core.send import BranchTask
    from chorusgraph.core.transport_router import TransportRouter


def encode_boundary_envelope(child_input: Dict[str, Any]) -> Dict[str, Any]:
    vector = list(child_input.get("vector") or [0.0] * 64)
    return {
        "envelope_id": str(child_input.get("envelope_id") or "boundary"),
        "vector_64": vector,
        "artifact_ref": compact_json({k: v for k, v in child_input.items() if k != "vector"}),
        "hop": "subgraph_boundary",
    }


def decode_boundary_envelope(frame: Dict[str, Any]) -> Dict[str, Any]:
    payload = frame.get("artifact_ref") or "{}"
    try:
        data = json.loads(payload) if isinstance(payload, str) else dict(payload)
    except json.JSONDecodeError:
        data = {"raw_output": str(payload)}
    data["vector"] = list(frame.get("vector_64") or [0.0] * 64)
    data["envelope_id"] = frame.get("envelope_id")
    return data


def _payload_vector(payload: Dict[str, Any], *, cache: Any = None) -> List[float]:
    from chorusgraph.core.send import _vector_for_payload

    return _vector_for_payload(payload, cache=cache)


def build_send_batch_frame(
    tasks: List["BranchTask"],
    *,
    tenant_id: str,
    cache: Any = None,
) -> ChorusBatchFrame:
    frames: List[ChorusFrame] = []
    for idx, task in enumerate(tasks):
        encoded = encode_boundary_envelope(dict(task.payload))
        frames.append(
            ChorusFrame(
                envelope_id=f"send-{idx}",
                vector_64=_payload_vector(task.payload, cache=cache),
                hop="send_batch",
                tenant_id=tenant_id,
                artifact_ref=str(encoded["artifact_ref"]),
                metadata={"branch_id": task.branch_id, "target": task.target},
            )
        )
    batch = encode_batch_frame(frames)
    batch.metadata["tenant_id"] = tenant_id
    return batch


def _invoke_child_values(
    spec: SubgraphSpec,
    child_input: Dict[str, Any],
    *,
    config: Dict[str, Any],
    parent_run_id: Optional[str],
) -> Dict[str, Any]:
    return spec.child.invoke(
        child_input,
        config=config,
        _parent_run_id=parent_run_id,
        _subgraph_node=spec.name,
    )


def invoke_remote_subgraph(
    spec: SubgraphSpec,
    child_input: Dict[str, Any],
    *,
    config: Dict[str, Any],
    parent_run_id: Optional[str] = None,
    transport: Optional["TransportRouter"] = None,
    boundary_translator: Any = None,
) -> Dict[str, Any]:
    """Encode → route → decode round-trip."""
    encoded = encode_boundary_envelope(child_input)
    tenant_id = str(config.get("configurable", {}).get("tenant_id") or "default")

    if spec.location == "chorus":
        spine = (
            transport.chorus
            if transport is not None and transport.chorus is not None
            else ChorusSpine(tenant_id=tenant_id)
        )
        frame = spine.encode_frame(
            envelope_id=str(encoded["envelope_id"]),
            vector_64=list(encoded["vector_64"]),
            hop=str(encoded["hop"]),
            artifact_ref=str(encoded["artifact_ref"]),
            metadata={"subgraph": spec.name, "parent_run_id": parent_run_id},
        )
        if transport is not None:
            transport.deliver_envelope(
                envelope_id=frame.envelope_id,
                vector_64=frame.vector_64,
                hop=frame.hop,
                artifact_ref=frame.artifact_ref,
                from_hop="parent",
                to_hop=spec.name,
            )
        else:
            spine.deliver(frame, from_hop="parent", to_hop=spec.name)
        routed = {
            "envelope_id": frame.envelope_id,
            "vector_64": frame.vector_64,
            "artifact_ref": frame.artifact_ref,
        }
    elif spec.location == "prismapi":
        spine = PrismAPISpine(
            tenant_id=tenant_id,
            client=getattr(transport, "prismapi_client", None) if transport else None,
            boundary_translator=boundary_translator,
        )
        routed = spine.route_envelope(encoded)
    else:
        raise ValueError(f"Unsupported remote subgraph location: {spec.location!r}")

    decoded = decode_boundary_envelope(routed)
    if boundary_translator is not None:
        from chorusgraph.core.subgraph import _maybe_reproject

        decoded = _maybe_reproject(decoded, translator=boundary_translator)
    return _invoke_child_values(spec, decoded, config=config, parent_run_id=parent_run_id)


def invoke_remote_send_batch(
    spec: SubgraphSpec,
    tasks: List["BranchTask"],
    *,
    config: Dict[str, Any],
    transport: Optional["TransportRouter"] = None,
    parent_run_id: Optional[str] = None,
    cache: Any = None,
    remote_executor: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Send-over-transport: one ChorusBatchFrame out, N branch results back.

    ``remote_executor(batch, spec, config)`` runs in the remote process when provided;
    otherwise falls back to sequential local ``invoke_remote_subgraph`` per task.
    """
    tenant_id = str(config.get("configurable", {}).get("tenant_id") or "default")
    batch = build_send_batch_frame(tasks, tenant_id=tenant_id, cache=cache)

    if transport is not None and transport.mode.value != "inproc":
        transport.deliver_batch(batch, from_hop="parent", to_hop=spec.name)

    if remote_executor is not None:
        return list(remote_executor(batch, spec, config))

    if transport is not None and transport.mode.value != "inproc":
        if hasattr(transport, "remote_batch_handler") and transport.remote_batch_handler is not None:
            return list(transport.remote_batch_handler(batch, spec, config))

    outputs: List[Dict[str, Any]] = []
    for task in tasks:
        child_input = decode_boundary_envelope(
            {
                "vector_64": _payload_vector(task.payload, cache=cache),
                "artifact_ref": compact_json(dict(task.payload)),
                "envelope_id": task.branch_id,
            }
        )
        values = invoke_remote_subgraph(
            spec,
            child_input,
            config=config,
            parent_run_id=parent_run_id,
            transport=transport,
        )
        artifact = {"branch_id": task.branch_id}
        for child_key, parent_key in spec.output_map.items():
            if child_key in values:
                artifact[parent_key] = values[child_key]
        outputs.append(artifact)
    return outputs


__all__ = [
    "build_send_batch_frame",
    "decode_boundary_envelope",
    "encode_boundary_envelope",
    "invoke_remote_send_batch",
    "invoke_remote_subgraph",
]
