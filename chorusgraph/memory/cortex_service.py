"""Cortex L3 memory — real prism_memory() stack."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key
from chorusgraph.memory.async_digest import AsyncDigester
from chorusgraph.memory.structured_recall import StructuredRecallContext, evidence_from_explain

_SHARED: Dict[str, "CortexMemoryService"] = {}


_EMPTY_RECALL = frozenset(
    {
        "i don't know.",
        "i don't know",
        "unknown.",
        "i do not have that information yet.",
    }
)


@dataclass
class RecallContext:
    answer: str
    confidence: float
    freshness: Optional[datetime]
    cache_hit: bool
    subgraph_hash: Optional[str] = None


@dataclass
class CortexMemoryService:
    """
    Persistent in-process Cortex memory service.

    GraphStore is InMemoryGraphStore — cross-session recall works while this
    service/process stays up. PrismLib answer cache is SQLite-durable.
    """

    tenant_id: str = "finance-tenant"
    cache_dir: str = ".chorusgraph/cortex"
    agent_id: str = "finance-agent"
    k: int = 8
    durable_graph: bool = True
    _memory: Any = None
    _digester: Optional[AsyncDigester] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        os.makedirs(self.cache_dir, exist_ok=True)

    def ensure_memory(self) -> Any:
        if self._memory is None:
            resolve_gemini_api_key()  # fail loud before constructing Gemini-backed Cortex
            from chorusgraph.memory.cortex_compat import apply_cortex_compat_patches

            apply_cortex_compat_patches()
            if self.durable_graph:
                from chorusgraph.persistence.cortex_factory import create_durable_prism_memory

                self._memory = create_durable_prism_memory(
                    tenant_id=self.tenant_id,
                    cache_dir=self.cache_dir,
                    k=self.k,
                )
            else:
                from prismcortex.adapters.prism import prism_memory

                self._memory = prism_memory(
                    tenant_id=self.tenant_id,
                    cache_db=os.path.join(self.cache_dir, "prismlib.db"),
                    resonance_state=os.path.join(self.cache_dir, "resonance_state.db"),
                    resonance_onnx=os.path.join(self.cache_dir, "resonance_engine.onnx"),
                    k=self.k,
                )
        return self._memory

    @property
    def digester(self) -> AsyncDigester:
        if self._digester is None:
            self._digester = AsyncDigester(self.ensure_memory)
        return self._digester

    def _recall_one(self, query: str) -> Optional[RecallContext]:
        mem = self.ensure_memory()
        result = mem.recall(query)
        answer = (result.answer or "").strip()
        if not answer or answer.lower() in _EMPTY_RECALL or answer.lower().startswith("i do not have"):
            return None
        return RecallContext(
            answer=answer,
            confidence=float(result.confidence or 0.0),
            freshness=result.freshness,
            cache_hit=bool(result.cache_hit),
            subgraph_hash=getattr(result, "subgraph_hash", None),
        )

    def recall(self, query: str) -> Optional[RecallContext]:
        return self._recall_one(query)

    def recall_for_turn(self, message: str) -> Optional[RecallContext]:
        """Recall for the user's message only — no demo profile fallback."""
        return self._recall_one(message)

    def recall_structured(
        self,
        query: str,
        *,
        cache: Any = None,
        profile_fallback: bool = False,
        raw_384: Any = None,
        vector_64: Optional[List[float]] = None,
    ) -> Optional[StructuredRecallContext]:
        """
        Vector + graph-fact recall for internal hops — no rendered prose.

        Cortex uses native **128-d** projection from shared raw_384 (H13).
        vector_64 (cache substrate) is stored for audit only when provided.
        """
        vector_128_list: List[float] = []
        vector_64_list: List[float] = list(vector_64 or [])
        category_slug = ""

        if raw_384 is not None:
            from chorusgraph.transforms.cortex_projector import project_cortex_from_raw

            slug, vec128, _ = project_cortex_from_raw(self.tenant_id, query, raw_384, k=self.k)
            vector_128_list = [float(x) for x in vec128]
            category_slug = slug
        elif cache is not None:
            from chorusgraph.transforms.cortex_projector import project_cortex_text

            slug, vec128, _ = project_cortex_text(self.tenant_id, query, k=self.k)
            vector_128_list = [float(x) for x in vec128]
            category_slug = slug
        elif vector_64:
            vector_64_list = [float(x) for x in vector_64]

        candidates = [query]
        if profile_fallback:
            candidates.append(
                "What are the user's stated preferences, risk tolerance, and investment profile?"
            )

        for candidate in candidates:
            mem = self.ensure_memory()
            explain = mem.explain(candidate)
            evidence = evidence_from_explain(explain)
            if not evidence:
                continue

            return StructuredRecallContext(
                query_vector_64=vector_64_list,
                query_vector_128=vector_128_list or None,
                category_slug=category_slug,
                evidence=evidence,
                confidence=float(explain.confidence or 0.0),
                freshness=explain.freshness,
                subgraph_hash=str(explain.subgraph_hash or ""),
            )
        return None

    def explain(self, query: str) -> Any:
        return self.ensure_memory().explain(query)

    def schedule_digest(self, text: str, *, source_id: str) -> None:
        """Async, off the response path — salience-gated inside Cortex digest()."""
        self.digester.submit_digest(text, source_id=source_id, agent_id=self.agent_id)

    def wait_for_digest(self, timeout: float = 120.0) -> None:
        self.digester.wait_idle(timeout=timeout)

    def schedule_sleep(self) -> None:
        """Consolidation pass — async, not on the hot path."""
        self.digester.submit_sleep()

    def forget(self, source_id: str) -> dict:
        """Right-to-forget — delegates to Cortex Memory.forget (graph + answer cache)."""
        return self.ensure_memory().forget(source_id)

    def on_event(self, callback: Any) -> Any:
        """
        Subscribe to PrismCortex 0.3.0 ``MemoryEvent`` notifications
        (accommodate / conflict / forget) for PrismShine cache invalidation.
        Returns an unsubscribe callable.
        """
        mem = self.ensure_memory()
        return mem.on_event(callback)

    def bind_cache_revalidate(self, sidecar: Any, *, threshold: float = 0.55) -> Any:
        """
        On Cortex correction/forget events, mark L1 sidecar rows for force refresh.

        Uses ``mark_revalidate`` with an embedding of the corrected subject/value text
        when available; otherwise a no-op for events without text.
        """
        from chorusgraph.cache_gate import mark_revalidate
        from chorusgraph.policy.embedder_guard import build_guarded_cache

        cache = build_guarded_cache(f"cortex-reval-{self.tenant_id}")

        def _handler(ev: Any) -> None:
            kind = getattr(getattr(ev, "kind", None), "value", None) or str(
                getattr(ev, "kind", "")
            )
            if kind not in ("accommodate", "forget", "conflict_resolved"):
                return
            parts = [
                getattr(ev, "subject", None) or "",
                getattr(ev, "relation", None) or "",
                getattr(ev, "new_value", None) or getattr(ev, "old_value", None) or "",
            ]
            text = " ".join(p for p in parts if p).strip()
            if not text:
                return
            try:
                raw = cache._embedder.embed(text)
                mark_revalidate(sidecar, query_vector=raw, threshold=threshold)
            except Exception:
                return

        return self.on_event(_handler)


def get_cortex_service(
    *,
    tenant_id: str = "finance-tenant",
    cache_dir: str = ".chorusgraph/cortex",
) -> CortexMemoryService:
    """Process-wide singleton so cross-session recall shares one GraphStore."""
    key = f"{tenant_id}:{os.path.abspath(cache_dir)}"
    if key not in _SHARED:
        _SHARED[key] = CortexMemoryService(tenant_id=tenant_id, cache_dir=cache_dir)
    return _SHARED[key]
