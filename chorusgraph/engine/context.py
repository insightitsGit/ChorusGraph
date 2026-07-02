"""Prism engine context — unified DI for all Prism family services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from chorusgraph.cache_gate.sidecar import SidecarStore
from chorusgraph.memory.cortex_service import CortexMemoryService
from chorusgraph.nodes.tool import ToolRegistry, default_finance_registry
from chorusgraph.policy.embedder_guard import build_guarded_cache


@dataclass
class PrismEngineContext:
    """
    Single runtime bag wiring the Prism data plane (DESIGN v0.3 §7).

    Passed to ``Graph.compile(context=...)`` and node factories.
    """

    tenant_id: str
    cache: Any = None
    sidecar: SidecarStore = field(default_factory=lambda: SidecarStore(":memory:"))
    tool_registry: ToolRegistry = field(default_factory=default_finance_registry)
    cortex: Optional[CortexMemoryService] = None
    cortex_cache_dir: str = ".chorusgraph/cortex"
    enable_cortex: bool = True
    session_artifacts: Dict[str, Any] = field(default_factory=dict)
    chorus_client: Any = None
    prismapi_client: Any = None

    def __post_init__(self) -> None:
        if self.cache is None:
            self.cache = build_guarded_cache(self.tenant_id)
        if self.enable_cortex and self.cortex is None:
            from chorusgraph.memory.cortex_service import get_cortex_service

            self.cortex = get_cortex_service(
                tenant_id=self.tenant_id,
                cache_dir=self.cortex_cache_dir,
            )

    @classmethod
    def from_finance_runtime(cls, runtime: Any) -> "PrismEngineContext":
        """Bridge existing FinanceRuntime to PrismEngineContext."""
        return cls(
            tenant_id=runtime.tenant_id,
            cache=runtime.cache,
            sidecar=runtime.sidecar,
            tool_registry=runtime.tool_registry,
            cortex=runtime.cortex,
            cortex_cache_dir=runtime.cortex_cache_dir,
            enable_cortex=runtime.enable_cortex,
            session_artifacts=dict(getattr(runtime, "session_tool_cache", {}) or {}),
        )

    def artifact_store(self) -> Dict[str, Any]:
        """Envelope artifact backing store (env:{id} keys)."""
        return self.session_artifacts
