"""Envelope channel state and reducers — L1 WRITE phase."""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional

from prismlang import PrismEnvelope

from chorusgraph.core.envelope import artifact_from_envelope_store, compact_json, make_envelope, store_artifact

ReducerFn = Callable[[Any, Any], Any]
PrismEnvelopeLike = Dict[str, Any]


DEFAULT_CHANNEL_REDUCERS: Dict[str, ReducerFn] = {
    "prism_sequence": operator.add,
    "rule_chain": operator.add,
    "vector_hops": operator.add,
}

APPEND_LIST_SCALAR_KEYS: frozenset[str] = frozenset(
    {
        "items",
        "conversation_history",
        "hop_metrics",
        "pipeline_trace",
        "tool_calls",
        "agent_trace",
        "vector_hops",
    }
)

# When parallel Send branches apply scalar updates sequentially, the last branch
# (by sorted branch_id) wins. Append-list keys accumulate all branch contributions.
BRANCH_SCALAR_COLLISION_RULE = "last_by_sorted_branch_id"

# Only these keys from the latest envelope artifact overlay view(); scalars win otherwise.
_ENVELOPE_OVERLAY_KEYS: frozenset[str] = frozenset(
    {"route", "response", "score", "raw_output", "category_slug", "cached_response"}
)


@dataclass
class NodeUpdate:
    """Envelope-native node output — no raw dict handoff on the bus."""

    envelopes: List[PrismEnvelopeLike] = field(default_factory=list)
    artifacts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    rule_chain: List[str] = field(default_factory=list)
    error_code: Optional[str] = None
    error_kind: Optional[str] = None
    retryable: Optional[bool] = None

    @property
    def primary(self) -> Optional[PrismEnvelopeLike]:
        return self.envelopes[-1] if self.envelopes else None


@dataclass
class ChannelState:
    """
    Mutable channel store for one graph run.

    The authoritative inter-node values are ``prism_sequence`` envelopes; ``_artifacts``
    holds decodable payloads keyed by ``envelope_id``.
    """

    seed: Dict[str, Any] = field(default_factory=dict)
    prism_sequence: List[PrismEnvelopeLike] = field(default_factory=list)
    rule_chain: List[str] = field(default_factory=list)
    vector_hops: List[Dict[str, Any]] = field(default_factory=list)
    _artifacts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    _scalars: Dict[str, Any] = field(default_factory=dict)
    latest_envelope_id: Optional[str] = None

    @classmethod
    def from_input(cls, input: Mapping[str, Any]) -> "ChannelState":
        state = cls(seed=dict(input))
        for key, value in input.items():
            if key in DEFAULT_CHANNEL_REDUCERS:
                if isinstance(value, list):
                    setattr(state, key, list(value))
            elif key not in ("prism_sequence", "rule_chain", "vector_hops", "_artifacts"):
                state._scalars[key] = value
        if input.get("prism_sequence"):
            state.prism_sequence = list(input["prism_sequence"])
        if input.get("rule_chain"):
            state.rule_chain = list(input["rule_chain"])
        if input.get("_artifacts"):
            state._artifacts = dict(input["_artifacts"])
        return state

    @classmethod
    def from_checkpoint_values(cls, values: Mapping[str, Any]) -> "ChannelState":
        state = cls(seed={})
        for key, value in values.items():
            if key == "prism_sequence" and isinstance(value, list):
                state.prism_sequence = list(value)
            elif key == "rule_chain" and isinstance(value, list):
                state.rule_chain = list(value)
            elif key == "vector_hops" and isinstance(value, list):
                state.vector_hops = list(value)
            elif key == "_artifacts" and isinstance(value, dict):
                state._artifacts = dict(value)
            elif key == "latest_envelope_id":
                state.latest_envelope_id = value
            elif key in DEFAULT_CHANNEL_REDUCERS:
                continue
            else:
                state._scalars[key] = value
        state.latest_envelope_id = values.get("latest_envelope_id") or state.latest_envelope_id
        return state

    def to_checkpoint_values(self) -> Dict[str, Any]:
        out = dict(self.seed)
        out.update(self._scalars)
        out["prism_sequence"] = list(self.prism_sequence)
        out["rule_chain"] = list(self.rule_chain)
        out["vector_hops"] = list(self.vector_hops)
        out["_artifacts"] = dict(self._artifacts)
        out["latest_envelope_id"] = self.latest_envelope_id
        return out

    def snapshot(self) -> "ChannelState":
        """Immutable read snapshot for one super-step (BSP read phase)."""
        return ChannelState(
            seed=dict(self.seed),
            prism_sequence=list(self.prism_sequence),
            rule_chain=list(self.rule_chain),
            vector_hops=list(self.vector_hops),
            _artifacts=dict(self._artifacts),
            _scalars=dict(self._scalars),
            latest_envelope_id=self.latest_envelope_id,
        )

    def view(self) -> Dict[str, Any]:
        """Merged dict view for node logic — derived from envelopes + seed."""
        out = dict(self.seed)
        out.update(self._scalars)
        out["prism_sequence"] = list(self.prism_sequence)
        out["rule_chain"] = list(self.rule_chain)
        out["vector_hops"] = list(self.vector_hops)
        out["latest_envelope_id"] = self.latest_envelope_id

        latest = self._latest_artifact()
        if latest:
            for key in _ENVELOPE_OVERLAY_KEYS:
                if key in latest:
                    out[key] = latest[key]
        return out

    def _latest_artifact(self) -> Dict[str, Any]:
        return artifact_from_envelope_store(self._artifacts, self.latest_envelope_id)

    def apply(
        self,
        update: NodeUpdate,
        *,
        reducers: Optional[Dict[str, ReducerFn]] = None,
    ) -> None:
        reducers = reducers or DEFAULT_CHANNEL_REDUCERS

        if update.rule_chain:
            self.rule_chain = reducers["rule_chain"](self.rule_chain, update.rule_chain)

        for env in update.envelopes:
            env_dict = env if isinstance(env, dict) else {
                "envelope_id": getattr(env, "envelope_id", None),
                "vector": list(getattr(env, "vector", []) or []),
                "agent_id": getattr(env, "agent_id", None),
                "category_slug": getattr(env, "category_slug", "general"),
                "rule_chain": list(getattr(env, "rule_chain", []) or []),
                "turn_id": getattr(env, "turn_id", 0),
            }
            self.prism_sequence = reducers["prism_sequence"](self.prism_sequence, [env_dict])
            self.latest_envelope_id = env_dict.get("envelope_id")

        for env_id, artifact in update.artifacts.items():
            store_artifact(self._artifacts, env_id, artifact)

        # Merge scalar/list fields from every artifact payload. dict_node_adapter may
        # attach an extra prism_sequence envelope whose id is not the publish primary.
        for artifact in update.artifacts.values():
            for key, value in artifact.items():
                if key in APPEND_LIST_SCALAR_KEYS and isinstance(value, list):
                    existing = self._scalars.get(key)
                    if isinstance(existing, list):
                        self._scalars[key] = existing + value
                    else:
                        self._scalars[key] = list(value)
                elif isinstance(value, dict):
                    self._scalars[key] = dict(value)
                elif isinstance(value, list):
                    self._scalars[key] = list(value)
                elif isinstance(value, (str, int, float, bool)) or value is None:
                    self._scalars[key] = value

        primary = update.primary
        if primary:
            if isinstance(primary, dict):
                primary_dict = primary
            else:
                primary_dict = {
                    "envelope_id": getattr(primary, "envelope_id", None),
                    "vector": getattr(primary, "vector", None),
                    "agent_id": getattr(primary, "agent_id", None),
                }

            vec = primary_dict.get("vector")
            vector_dim = len(list(vec)) if vec is not None else 0
            self.vector_hops = reducers.get("vector_hops", operator.add)(
                self.vector_hops,
                [
                    {
                        "hop": primary_dict.get("agent_id"),
                        "vector_dim": vector_dim,
                        "envelope_id": primary_dict.get("envelope_id"),
                    }
                ],
            )


def publish_update(
    *,
    hop: str,
    artifact: Dict[str, Any],
    vector: List[float],
    category_slug: str,
    rule_chain: List[str],
    turn_id: int,
) -> NodeUpdate:
    env = make_envelope(
        hop=hop,
        artifact=artifact,
        vector=vector,
        category_slug=category_slug,
        rule_chain=rule_chain,
        turn_id=turn_id,
    )
    env_id = env["envelope_id"]
    return NodeUpdate(
        envelopes=[env],
        artifacts={env_id: artifact},
        rule_chain=list(rule_chain),
    )


__all__ = [
    "ChannelState",
    "DEFAULT_CHANNEL_REDUCERS",
    "NodeUpdate",
    "publish_update",
]
