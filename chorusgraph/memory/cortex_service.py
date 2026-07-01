"""Cortex L3 memory — real prism_memory() stack."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key
from chorusgraph.memory.async_digest import AsyncDigester

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
    _memory: Any = None
    _digester: Optional[AsyncDigester] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        os.makedirs(self.cache_dir, exist_ok=True)

    def ensure_memory(self) -> Any:
        if self._memory is None:
            resolve_gemini_api_key()  # fail loud before constructing Gemini-backed Cortex
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
        """Budgeted recall — question first, then general profile fallback."""
        for candidate in (
            message,
            "What are the user's stated preferences, risk tolerance, and investment profile?",
        ):
            ctx = self._recall_one(candidate)
            if ctx:
                return ctx
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
