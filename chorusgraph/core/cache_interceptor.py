"""Node-entry cache interceptor — deterministic-first (P4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, TYPE_CHECKING

import numpy as np

from chorusgraph.cache_gate.decision import Decision
from chorusgraph.cache_gate.gate import gate
from chorusgraph.core.channels import NodeUpdate, publish_update
from chorusgraph.sections.models import CachePolicy, Section
from chorusgraph.transforms.projector import raw_from_state, vector_64_from_state

if TYPE_CHECKING:
    from prism.cache import PrismCache

    from chorusgraph.cache_gate.sidecar import SidecarStore


@dataclass
class CacheRuntime:
    """Cache + sidecar bundle for node-entry gate evaluation."""

    cache: "PrismCache"
    sidecar: "SidecarStore"
    coarse_threshold: float = 0.88
    verify_threshold: float = 0.95


@dataclass
class NodeCacheSpec:
    node_id: str
    category_slug: str = "general"
    cache_policy: CachePolicy = CachePolicy.NO_CACHE
    query_key: str = "message"


class CacheInterceptor:
    """Evaluate cache_gate before node body — skip execution on verified hit."""

    def __init__(self, runtime: CacheRuntime, specs: Dict[str, NodeCacheSpec]) -> None:
        self._runtime = runtime
        self._specs = specs

    def try_skip(
        self,
        node_id: str,
        view: Dict[str, Any],
        *,
        super_step: int,
    ) -> Optional[tuple[NodeUpdate, Decision]]:
        spec = self._specs.get(node_id)
        if spec is None or spec.cache_policy == CachePolicy.NO_CACHE:
            return None

        query = str(view.get(spec.query_key) or view.get("message") or "")
        if not query.strip():
            return None

        section = Section(
            section_id=f"{node_id}_cache",
            category_slug=spec.category_slug,
            content=query,
            cache_policy=spec.cache_policy,
        )
        raw = raw_from_state(view)
        vec = vector_64_from_state(view)
        decision = gate(
            query,
            section,
            self._runtime.cache,
            self._runtime.sidecar,
            coarse_threshold=self._runtime.coarse_threshold,
            verify_threshold=self._runtime.verify_threshold,
            raw_embedding_384=np.asarray(raw, dtype=np.float32) if raw is not None else None,
            projected_vector_64=np.asarray(vec, dtype=np.float32) if vec is not None else None,
        )
        if not decision.is_hit or not decision.value:
            return None

        artifact = dict(decision.value)
        artifact.setdefault("_cache_hit", True)
        artifact.setdefault("cache_hit", True)
        update = publish_update(
            hop=node_id,
            artifact=artifact,
            vector=list(vec) if vec is not None else [0.0] * 64,
            category_slug=spec.category_slug,
            rule_chain=[f"cache_hit={decision.kind.value}", f"score={decision.verify_score or decision.coarse_score:.3f}"],
            turn_id=super_step,
        )
        return update, decision


__all__ = ["CacheInterceptor", "CacheRuntime", "NodeCacheSpec"]
