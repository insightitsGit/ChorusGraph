"""Dynamic fan-out — Send API (Improve-1 T3)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from chorusgraph.core.channels import NodeUpdate

JoinSpec = Union[str, Tuple[str, int], Tuple[str, float]]

COARSE_DEDUP_THRESHOLD = 0.88


@dataclass(frozen=True)
class Send:
    """Dynamic branch dispatch — target node + branch-local payload."""

    target: str
    payload: Dict[str, Any]


@dataclass
class BranchTask:
    """One deduplicated branch execution."""

    branch_id: str
    target: str
    payload: Dict[str, Any]
    request_indices: List[int] = field(default_factory=list)


def branch_id_for(send_node: str, super_step: int, index: int) -> str:
    return f"{send_node}:{super_step}:{index}"


def _payload_key(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _vector_for_payload(payload: Dict[str, Any], cache: Any = None) -> List[float]:
    if cache is not None and hasattr(cache, "_projector"):
        from chorusgraph.core.envelope import compact_json

        _, envelope = cache._projector.project(compact_json(payload))
        return [float(x) for x in envelope.vector]
    # Deterministic pseudo-vector from payload when no projector (tests).
    digest = _payload_key(payload)
    out = [0.0] * 64
    for i, ch in enumerate(digest.encode("utf-8")):
        out[i % 64] += float(ch) / 255.0
    return out


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(dot / (na * nb))


def dedup_sends(
    sends: Sequence[Send],
    *,
    send_node: str,
    super_step: int,
    cache: Any = None,
    coarse_threshold: float = COARSE_DEDUP_THRESHOLD,
) -> Tuple[List[BranchTask], List[int]]:
    """
    Merge duplicate branch payloads (64-d coarse or exact key fallback).

    Returns (executable tasks, map from each send index -> task index).
    """
    if not sends:
        return [], []

    vectors = [_vector_for_payload(s.payload, cache) for s in sends]
    groups: List[BranchTask] = []
    send_to_task: List[int] = []
    use_vector = cache is not None and hasattr(cache, "_projector")

    for idx, (send, vec) in enumerate(zip(sends, vectors)):
        merged = False
        for g_idx, task in enumerate(groups):
            if _payload_key(send.payload) == _payload_key(task.payload):
                task.request_indices.append(idx)
                send_to_task.append(g_idx)
                merged = True
                break
            if use_vector:
                g_vec = _vector_for_payload(task.payload, cache)
                if _cosine(vec, g_vec) >= coarse_threshold:
                    task.request_indices.append(idx)
                    send_to_task.append(g_idx)
                    merged = True
                    break
        if not merged:
            bid = branch_id_for(send_node, super_step, len(groups))
            groups.append(
                BranchTask(
                    branch_id=bid,
                    target=send.target,
                    payload=dict(send.payload),
                    request_indices=[idx],
                )
            )
            send_to_task.append(len(groups) - 1)

    return groups, send_to_task


@dataclass
class SendBatch:
    """In-flight dynamic fan-out scheduled after a map node."""

    send_node: str
    super_step: int
    tasks: List[BranchTask]
    send_to_task: List[int]
    join_node: str
    join_spec: JoinSpec
    branches_requested: int
    branches_executed: int
    completed: Dict[str, NodeUpdate] = field(default_factory=dict)
    join_activated: bool = False
    branch_start_ms: float = 0.0
    fan_results: List[Optional[Dict[str, Any]]] = field(default_factory=list)
    parent_snapshot: Any = None
    remote_subgraph_spec: Any = None
    remote_executed: bool = False
    resumed_branch_ids: set[str] = field(default_factory=set)
    remote_branch_outputs: Optional[List[Dict[str, Any]]] = None


def join_threshold(spec: JoinSpec, total: int) -> int:
    if spec == "all" or spec is None:
        return total
    if isinstance(spec, tuple) and spec[0] == "quorum":
        k = int(spec[1])
        return min(max(k, 1), total)
    if isinstance(spec, tuple) and spec[0] == "timeout":
        return 1
    return total


def join_satisfied(
    spec: JoinSpec,
    *,
    completed: int,
    total: int,
    elapsed_ms: float,
) -> bool:
    if spec == "all" or spec is None:
        return completed >= total
    if isinstance(spec, tuple) and spec[0] == "quorum":
        return completed >= join_threshold(spec, total)
    if isinstance(spec, tuple) and spec[0] == "timeout":
        limit_ms = float(spec[1])
        return elapsed_ms >= limit_ms or completed >= total
    return completed >= total


__all__ = [
    "BranchTask",
    "COARSE_DEDUP_THRESHOLD",
    "JoinSpec",
    "Send",
    "SendBatch",
    "branch_id_for",
    "dedup_sends",
    "join_satisfied",
    "join_threshold",
]
