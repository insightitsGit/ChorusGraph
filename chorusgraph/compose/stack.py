"""ChorusStack — compose engine + swappable section backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from chorusgraph.cache_gate.sidecar import SidecarStore
from chorusgraph.compose.adapters.prism_cache import PrismCacheBackend
from chorusgraph.compose.defaults import (
    default_checkpointer,
    default_ledger_sink,
    default_memory_backend,
    default_prism_cache_backend,
    default_sidecar,
    default_tool_registry,
)
from chorusgraph.compose.ports import CacheBackend, MemoryBackend, ToolBackend
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
    coarse_threshold: float = 0.88
    verify_threshold: float = 0.95
    enable_memory: bool = True
    cortex_cache_dir: str = ".chorusgraph/cortex"
    checkpoint_root: str = ".chorusgraph/checkpoints"
    ledger_path: str = ":memory:"
    sidecar_path: str = ":memory:"
    _cache_runtime: Optional[Any] = field(default=None, repr=False)

    @classmethod
    def defaults(cls, *, tenant_id: str = "default", **kwargs: Any) -> "ChorusStack":
        """Full Prism stack — ready to run without extra wiring."""
        return cls(tenant_id=tenant_id, **kwargs)

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

    def resolve_checkpointer(self) -> EngineCheckpointer:
        if self.checkpointer is None:
            self.checkpointer = default_checkpointer(self.checkpoint_root)
        return self.checkpointer

    def resolve_ledger(self) -> LedgerSink:
        if self.ledger is None:
            self.ledger = default_ledger_sink(self.ledger_path)
        return self.ledger

    def resolve_tools(self) -> ToolBackend:
        if self.tools is None:
            self.tools = default_tool_registry()
        return self.tools

    def to_cache_runtime(self) -> Any:
        """Build ``CacheRuntime`` for node-entry cache interceptor."""
        if self._cache_runtime is not None:
            return self._cache_runtime
        from chorusgraph.core.cache_interceptor import CacheRuntime

        backend = self.resolve_cache()
        sidecar = self.resolve_sidecar()
        if isinstance(backend, PrismCacheBackend):
            cache = backend.cache
        else:
            cache = backend
        self._cache_runtime = CacheRuntime(
            cache=cache,
            sidecar=sidecar,
            coarse_threshold=self.coarse_threshold,
            verify_threshold=self.verify_threshold,
            tenant_id=self.tenant_id,
            registry=default_registry(),
            backend=backend,
        )
        return self._cache_runtime

    def with_cache(self, backend: CacheBackend) -> "ChorusStack":
        """Return a copy with cache backend replaced (e.g. Redis)."""
        return ChorusStack(
            tenant_id=self.tenant_id,
            cache=backend,
            sidecar=self.sidecar,
            memory=self.memory,
            checkpointer=self.checkpointer,
            ledger=self.ledger,
            tools=self.tools,
            coarse_threshold=self.coarse_threshold,
            verify_threshold=self.verify_threshold,
            enable_memory=self.enable_memory,
            cortex_cache_dir=self.cortex_cache_dir,
            checkpoint_root=self.checkpoint_root,
            ledger_path=self.ledger_path,
            sidecar_path=self.sidecar_path,
        )


__all__ = ["ChorusStack"]
