"""Shared runtime for finance agent graph — composes ``ChorusStack`` defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from chorusgraph.cache_gate.sidecar import SidecarStore
from chorusgraph.compose import ChorusStack, PrismCacheBackend
from chorusgraph.compose.ports import CacheBackend
from chorusgraph.examples.finance_agent.gemini_client import GeminiClient
from chorusgraph.memory.cortex_service import CortexMemoryService
from chorusgraph.nodes.tool import ToolRegistry, default_finance_registry


@dataclass
class FinanceRuntime:
    """
    Session runtime for finance / benchmark graphs.

    Wraps ``ChorusStack`` — full Prism product by default; swap ``stack.cache``
    (e.g. ``RedisCacheBackend``) without changing graph code.
    """

    tenant_id: str = "finance-tenant"
    stack: Optional[ChorusStack] = None
    tool_registry: ToolRegistry = field(default_factory=default_finance_registry)
    sidecar: SidecarStore = field(default_factory=lambda: SidecarStore(":memory:"))
    gemini: Optional[GeminiClient] = None
    cortex: Optional[CortexMemoryService] = None
    cortex_cache_dir: str = ".chorusgraph/cortex"
    session_tool_cache: Dict[str, Any] = field(default_factory=dict)
    enable_cortex: bool = True
    _cache_override: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.stack is None:
            cache_backend: Optional[CacheBackend] = None
            if self._cache_override is not None:
                cache_backend = (
                    self._cache_override
                    if isinstance(self._cache_override, CacheBackend)
                    else PrismCacheBackend(self._cache_override, self.sidecar)
                )
            self.stack = ChorusStack.defaults(
                tenant_id=self.tenant_id,
                cache=cache_backend,
                sidecar=self.sidecar,
                enable_memory=self.enable_cortex,
                cortex_cache_dir=self.cortex_cache_dir,
                tools=self.tool_registry,
            )
        if self.cortex is None and self.enable_cortex:
            mem = self.stack.resolve_memory()
            if mem is not None and hasattr(mem, "service"):
                self.cortex = mem.service  # type: ignore[assignment]

    def __init__(
        self,
        tenant_id: str = "finance-tenant",
        *,
        stack: Optional[ChorusStack] = None,
        tool_registry: Optional[ToolRegistry] = None,
        sidecar: Optional[SidecarStore] = None,
        cache: Any = None,
        gemini: Optional[GeminiClient] = None,
        cortex: Optional[CortexMemoryService] = None,
        cortex_cache_dir: str = ".chorusgraph/cortex",
        session_tool_cache: Optional[Dict[str, Any]] = None,
        enable_cortex: bool = True,
    ) -> None:
        self.tenant_id = tenant_id
        self.stack = stack
        self.tool_registry = tool_registry or default_finance_registry()
        self.sidecar = sidecar or SidecarStore(":memory:")
        self.gemini = gemini
        self.cortex = cortex
        self.cortex_cache_dir = cortex_cache_dir
        self.session_tool_cache = session_tool_cache if session_tool_cache is not None else {}
        self.enable_cortex = enable_cortex
        self._cache_override = cache
        self.__post_init__()

    @property
    def cache(self) -> Any:
        """Legacy PrismCache when using default backend; else ``CacheBackend``."""
        backend = self.stack.resolve_cache()
        if isinstance(backend, PrismCacheBackend):
            return backend.cache
        return backend

    def ensure_gemini(self) -> GeminiClient:
        if self.gemini is None:
            self.gemini = GeminiClient()
        return self.gemini

    @property
    def cache_backend(self) -> CacheBackend:
        return self.stack.resolve_cache()

    def seed_tool_cache(
        self,
        query_key: str,
        tool_result: Dict[str, Any],
        *,
        category_slug: str = "fx_rates",
    ) -> None:
        from chorusgraph.cache_gate import seed_cache_entry

        backend = self.stack.resolve_cache()
        sidecar = self.stack.resolve_sidecar()
        seed_cache_entry(
            backend,
            sidecar,
            query=query_key,
            value=tool_result,
            category_slug=category_slug,
            cache_policy="replay_safe",
        )
        self.session_tool_cache[query_key] = tool_result

    def schedule_turn_digest(self, user_message: str, assistant_response: str, *, turn_id: str) -> None:
        if not self.cortex or not assistant_response.strip():
            return
        payload = f"User: {user_message}\nAssistant: {assistant_response}"
        self.cortex.schedule_digest(payload, source_id=turn_id)
