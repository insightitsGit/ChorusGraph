"""Node-entry cache interceptor — deterministic-first (P4) + CacheProfile (H21)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar, TYPE_CHECKING

import numpy as np

from chorusgraph.cache_gate.decision import Decision
from chorusgraph.cache_gate.flight import (
    FlightPolicy,
    InProcessFlightCoordinator,
    flight_eligible,
    resolve_flight_policy,
)
from chorusgraph.cache_gate.gate import gate
from chorusgraph.cache_gate.scope import scope_id as make_scope_id
from chorusgraph.compose.ports import CacheBackend, is_cache_backend
from chorusgraph.core.channels import NodeUpdate, publish_update
from chorusgraph.sections.models import CachePolicy, CacheProfile, Section
from chorusgraph.sections.profiles import default_registry
from chorusgraph.transforms.projector import raw_from_state, vector_64_from_state

if TYPE_CHECKING:
    from chorusgraph.cache_gate.sidecar import SidecarStore

T = TypeVar("T")


@dataclass
class CacheRuntime:
    """Cache + sidecar bundle for node-entry gate evaluation."""

    cache: Any
    sidecar: "SidecarStore"
    coarse_threshold: float = 0.88
    verify_threshold: Optional[float] = None
    measured_thresholds: Optional[Any] = None
    tenant_id: str = "default"
    registry: Any = field(default_factory=default_registry)
    backend: Optional[CacheBackend] = None
    # ADR-006 — default off; no stampede join unless enabled.
    flight_policy: FlightPolicy = field(default_factory=FlightPolicy)
    flight: Optional[InProcessFlightCoordinator] = None

    def verify_threshold_for(self, category_slug: str) -> float:
        if self.verify_threshold is not None:
            return self.verify_threshold
        if self.measured_thresholds is not None:
            return self.measured_thresholds.verify_for(category_slug)
        return 0.95

    def resolve_backend(self) -> CacheBackend:
        if self.backend is not None:
            return self.backend
        if isinstance(self.cache, CacheBackend) or is_cache_backend(self.cache):
            return self.cache
        from chorusgraph.compose.adapters.prism_cache import PrismCacheBackend

        return PrismCacheBackend(self.cache, self.sidecar)

    def resolve_flight(self) -> InProcessFlightCoordinator:
        if self.flight is None:
            self.flight = InProcessFlightCoordinator()
        return self.flight


@dataclass
class NodeCacheSpec:
    node_id: str
    category_slug: str = "general"
    cache_policy: CachePolicy = CachePolicy.NO_CACHE
    query_key: str = "message"
    profile: Optional[CacheProfile] = None
    fingerprint_key: str = "fingerprint_key"
    scope_session_key: str = "session_id"
    scope_user_key: str = "user_id"
    flight_policy: Optional[FlightPolicy] = None


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
        if not query.strip() and spec.profile and spec.profile.keying != "fingerprint":
            return None

        profile = self._runtime.registry.get(spec.category_slug, override=spec.profile)
        fp_key = str(view.get(spec.fingerprint_key) or "") if profile.keying == "fingerprint" else None
        sid = make_scope_id(
            profile.scope,
            tenant_id=self._runtime.tenant_id,
            user_id=str(view.get(spec.scope_user_key) or "") or None,
            session_id=str(view.get(spec.scope_session_key) or "") or None,
        )

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
            self._runtime.resolve_backend(),
            coarse_threshold=self._runtime.coarse_threshold,
            verify_threshold=self._runtime.verify_threshold_for(spec.category_slug),
            profile=profile,
            scope_id=sid,
            fingerprint_key=fp_key,
            tenant_id=self._runtime.tenant_id,
            user_id=str(view.get(spec.scope_user_key) or "") or None,
            session_id=str(view.get(spec.scope_session_key) or "") or None,
            raw_embedding_384=np.asarray(raw, dtype=np.float32) if raw is not None else None,
            projected_vector_64=np.asarray(vec, dtype=np.float32) if vec is not None else None,
        )
        if not decision.is_hit or not decision.value:
            return None
        # PrismShine mark_revalidate — must re-run body; do not skip.
        if getattr(decision, "force_refresh", False):
            return None

        artifact = dict(decision.value) if isinstance(decision.value, dict) else {"value": decision.value}
        artifact.setdefault("_cache_hit", True)
        artifact.setdefault("cache_hit", True)
        rules = [
            f"cache_hit={decision.kind.value}",
            f"score={decision.verify_score or decision.coarse_score:.3f}",
        ]
        if decision.created_at is not None:
            rules.append(f"created_at={decision.created_at}")
        update = publish_update(
            hop=node_id,
            artifact=artifact,
            vector=list(vec) if vec is not None else [0.0] * 64,
            category_slug=spec.category_slug,
            rule_chain=rules,
            turn_id=super_step,
        )
        return update, decision

    def _miss_flight_plan(
        self, node_id: str, view: Dict[str, Any]
    ) -> Optional[tuple[str, FlightPolicy]]:
        spec = self._specs.get(node_id)
        if spec is None or spec.cache_policy == CachePolicy.NO_CACHE:
            return None

        profile = self._runtime.registry.get(spec.category_slug, override=spec.profile)
        policy = resolve_flight_policy(
            runtime_policy=self._runtime.flight_policy,
            spec_policy=spec.flight_policy,
            profile=profile,
        )
        if not policy.enabled:
            return None

        query = str(view.get(spec.query_key) or view.get("message") or "")
        fp_key = str(view.get(spec.fingerprint_key) or "") if profile.keying == "fingerprint" else None
        sid = make_scope_id(
            profile.scope,
            tenant_id=self._runtime.tenant_id,
            user_id=str(view.get(spec.scope_user_key) or "") or None,
            session_id=str(view.get(spec.scope_session_key) or "") or None,
        )
        elig = flight_eligible(
            profile,
            tenant_id=self._runtime.tenant_id,
            scope_id=sid,
            category_slug=spec.category_slug,
            query=query,
            fingerprint_key=fp_key,
            policy=policy,
        )
        if not elig.eligible or not elig.flight_key:
            return None
        return elig.flight_key, policy

    def run_miss(self, node_id: str, view: Dict[str, Any], compute: Callable[[], T]) -> T:
        """Run miss-path ``compute``, joining an in-flight peer when eligible."""
        plan = self._miss_flight_plan(node_id, view)
        if plan is None:
            return compute()
        key, policy = plan
        return self._runtime.resolve_flight().run(
            key,
            compute,
            timeout_s=policy.join_timeout_s,
            on_leader_error=policy.on_leader_error,
        )

    async def arun_miss(
        self, node_id: str, view: Dict[str, Any], compute: Callable[[], Awaitable[T]]
    ) -> T:
        plan = self._miss_flight_plan(node_id, view)
        if plan is None:
            return await compute()
        key, policy = plan
        return await self._runtime.resolve_flight().arun(
            key,
            compute,
            timeout_s=policy.join_timeout_s,
            on_leader_error=policy.on_leader_error,
        )


__all__ = ["CacheInterceptor", "CacheRuntime", "NodeCacheSpec"]
