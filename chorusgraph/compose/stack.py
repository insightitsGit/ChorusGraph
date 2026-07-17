"""ChorusStack — compose engine + swappable section backends."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Optional

from chorusgraph.cache_gate.sidecar import SidecarStore
from chorusgraph.cache_gate.thresholds import CacheThresholds, measured_thresholds
from chorusgraph.compose.adapters.prism_cache import PrismCacheBackend
from chorusgraph.compose.adapters.persistence import SqlitePersistenceBackend
from chorusgraph.compose.defaults import (
    default_checkpointer,
    default_ledger_sink,
    default_memory_backend,
    default_prism_cache_backend,
    default_retrieval_backend,
    default_sidecar,
    default_tool_registry,
)
from chorusgraph.compose.ports import CacheBackend, MemoryBackend, PersistenceBackend, RetrievalBackend, ToolBackend
from chorusgraph.core.persistence import EngineCheckpointer
from chorusgraph.ledger.sink import LedgerSink
from chorusgraph.sections.profiles import default_registry


@dataclass
class ChorusStack:
    """
    Product composition root — wire once, pass to ``Graph.compile(stack=...)``.

    **Engine-fixed** (not swappable): PrismLang projection, Resonance bus routing,
    CHORUS transport interface, BSP scheduler, envelope channels.

    **Default attached** (full product, one package): PrismCache, SidecarStore,
    Cortex memory, JSON checkpointer, SQLite ledger, finance tool registry.

    **Swappable**: pass ``cache=RedisCacheBackend(...)``, external checkpointer,
    disable memory with ``enable_memory=False``, etc.
    """

    tenant_id: str = "default"
    cache: Optional[CacheBackend] = None
    sidecar: Optional[SidecarStore] = None
    memory: Optional[MemoryBackend] = None
    checkpointer: Optional[EngineCheckpointer] = None
    ledger: Optional[LedgerSink] = None
    tools: Optional[ToolBackend] = None
    retrieval: Optional[RetrievalBackend] = None
    persistence: Optional[PersistenceBackend] = None
    coarse_threshold: Optional[float] = None
    verify_threshold: Optional[float] = None
    enable_memory: bool = True
    cortex_cache_dir: str = ".chorusgraph/cortex"
    checkpoint_root: str = ".chorusgraph/checkpoints"
    ledger_path: str = ":memory:"
    sidecar_path: str = ":memory:"
    flight_policy: Optional[Any] = None
    _cache_runtime: Optional[Any] = field(default=None, repr=False)
    _measured_thresholds: Optional[CacheThresholds] = field(default=None, repr=False)

    @classmethod
    def defaults(cls, *, tenant_id: str = "default", **kwargs: Any) -> "ChorusStack":
        """Full Prism stack — ready to run without extra wiring."""
        return cls(tenant_id=tenant_id, **kwargs)

    def resolve_measured_thresholds(self) -> CacheThresholds:
        if self._measured_thresholds is None:
            self._measured_thresholds = measured_thresholds()
        return self._measured_thresholds

    def resolve_sidecar(self) -> SidecarStore:
        if self.sidecar is None:
            self.sidecar = default_sidecar(self.sidecar_path)
        return self.sidecar

    def resolve_cache(self) -> CacheBackend:
        if self.cache is None:
            self.cache = default_prism_cache_backend(
                self.tenant_id,
                sidecar=self.resolve_sidecar(),
            )
        return self.cache

    def resolve_memory(self) -> Optional[MemoryBackend]:
        if not self.enable_memory:
            return None
        if self.memory is None:
            self.memory = default_memory_backend(
                tenant_id=self.tenant_id,
                cache_dir=self.cortex_cache_dir,
            )
        return self.memory

    def resolve_persistence(self) -> PersistenceBackend:
        if self.persistence is None:
            self.persistence = SqlitePersistenceBackend()
        return self.persistence

    def resolve_checkpointer(self) -> EngineCheckpointer:
        if self.checkpointer is None:
            backend = self.resolve_persistence()
            self.checkpointer = backend.make_checkpointer(checkpoint_root=self.checkpoint_root)
        return self.checkpointer

    def resolve_graph_store(self, *, graph_path: str | None = None) -> Any:
        path = graph_path or str(Path(self.cortex_cache_dir) / "graph_store.db")
        return self.resolve_persistence().make_graph_store(
            graph_path=path,
            tenant_id=self.tenant_id,
        )

    def resolve_ledger(self) -> LedgerSink:
        if self.ledger is None:
            self.ledger = default_ledger_sink(self.ledger_path)
        return self.ledger

    def resolve_tools(self) -> ToolBackend:
        if self.tools is None:
            self.tools = default_tool_registry()
        return self.tools

    def resolve_retrieval(self) -> RetrievalBackend:
        if self.retrieval is None:
            self.retrieval = default_retrieval_backend()
        return self.retrieval

    def to_cache_runtime(self) -> Any:
        """Build ``CacheRuntime`` for node-entry cache interceptor."""
        if self._cache_runtime is not None:
            return self._cache_runtime
        from chorusgraph.cache_gate.flight import FlightPolicy
        from chorusgraph.core.cache_interceptor import CacheRuntime

        thresholds = self.resolve_measured_thresholds()
        coarse = self.coarse_threshold if self.coarse_threshold is not None else thresholds.coarse
        backend = self.resolve_cache()
        sidecar = self.resolve_sidecar()
        if isinstance(backend, PrismCacheBackend):
            cache = backend.cache
        else:
            cache = backend
        policy = self.flight_policy if self.flight_policy is not None else FlightPolicy()
        self._cache_runtime = CacheRuntime(
            cache=cache,
            sidecar=sidecar,
            coarse_threshold=coarse,
            verify_threshold=self.verify_threshold,
            measured_thresholds=thresholds if self.verify_threshold is None else None,
            tenant_id=self.tenant_id,
            registry=default_registry(),
            backend=backend,
            flight_policy=policy,
        )
        return self._cache_runtime

    def with_cache(self, backend: CacheBackend) -> "ChorusStack":
        """Return a copy with cache backend replaced (e.g. Redis)."""
        return replace(self, cache=backend, _cache_runtime=None)

    def with_flight(self, policy: Any) -> "ChorusStack":
        """Return a copy with L1 single-flight policy (ADR-006; default remains off)."""
        return replace(self, flight_policy=policy, _cache_runtime=None)

    def with_retrieval(self, backend: RetrievalBackend) -> "ChorusStack":
        """Return a copy with retrieval backend replaced (e.g. PrismRAG)."""
        return replace(self, retrieval=backend)

    def with_persistence(self, backend: PersistenceBackend) -> "ChorusStack":
        """Return a copy with persistence backend replaced (e.g. licensed Postgres)."""
        return replace(self, persistence=backend, checkpointer=None)

    def to_retrieve_handler(
        self,
        *,
        topic: str = "knowledge",
        top_k: int = 6,
        runtime: Any = None,
        partition: Optional[str] = None,
        rerank_policy: str = "embed_missing",
        require_chunk_vectors: bool = False,
    ) -> Any:
        """Build retrieve node wired to ``resolve_retrieval()``.

        Optional warm chunk-vector knobs (``partition``, ``rerank_policy``,
        ``require_chunk_vectors``) default to 1.0.x-compatible behavior.
        """
        from chorusgraph.nodes.retrieve import RetrieveConfig, make_retrieve_handler

        backend = self.resolve_retrieval()
        cfg = RetrieveConfig(
            category_slug=topic,
            top_k=top_k,
            rerank_policy=rerank_policy,  # type: ignore[arg-type]
            require_chunk_vectors=require_chunk_vectors,
            partition=partition,
        )
        cache = None
        if runtime is not None:
            cache = getattr(runtime, "cache", None)
        if cache is None:
            cache_backend = self.resolve_cache()
            if isinstance(cache_backend, PrismCacheBackend):
                cache = cache_backend.cache

        def _retrieve_fn(t: str, q: str):
            return list(
                backend.retrieve(t or topic, q, top_k=top_k, partition=partition)
            )

        return make_retrieve_handler(_retrieve_fn, cache=cache, config=cfg)

    def warm_retrieval(self, partition: Optional[str] = None) -> "ChorusStack":
        """Idempotent L2 warm — delegates to backend ``warm`` when present."""
        backend = self.resolve_retrieval()
        warm = getattr(backend, "warm", None)
        if callable(warm):
            warm(partition=partition)
        return self

    def retrieval_ready(self, partition: Optional[str] = None) -> bool:
        """True when retrieval partition(s) are warm (or backend has no readiness API)."""
        backend = self.resolve_retrieval()
        ready = getattr(backend, "is_ready", None)
        if callable(ready):
            return bool(ready(partition=partition))
        return True

    def retrieval_stats(self) -> Any:
        """Return backend ``RetrievalStats`` when available."""
        backend = self.resolve_retrieval()
        stats_fn = getattr(backend, "stats", None)
        if callable(stats_fn):
            return stats_fn()
        return None


__all__ = ["ChorusStack"]
