"""Shared runtime for finance agent graph (cache, tools, Gemini, Cortex)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from chorusgraph.cache_gate.sidecar import SidecarStore
from chorusgraph.examples.finance_agent.gemini_client import GeminiClient
from chorusgraph.memory.cortex_service import CortexMemoryService, get_cortex_service
from chorusgraph.nodes.tool import ToolRegistry, default_finance_registry
from chorusgraph.policy.embedder_guard import build_guarded_cache


@dataclass
class FinanceRuntime:
    tenant_id: str = "finance-tenant"
    tool_registry: ToolRegistry = field(default_factory=default_finance_registry)
    sidecar: SidecarStore = field(default_factory=lambda: SidecarStore(":memory:"))
    cache: Any = None
    gemini: Optional[GeminiClient] = None
    cortex: Optional[CortexMemoryService] = None
    cortex_cache_dir: str = ".chorusgraph/cortex"
    session_tool_cache: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.cache is None:
            self.cache = build_guarded_cache(self.tenant_id)
        if self.cortex is None:
            self.cortex = get_cortex_service(
                tenant_id=self.tenant_id,
                cache_dir=self.cortex_cache_dir,
            )

    def ensure_gemini(self) -> GeminiClient:
        if self.gemini is None:
            self.gemini = GeminiClient()
        return self.gemini

    def seed_tool_cache(self, query_key: str, tool_result: Dict[str, Any]) -> None:
        from chorusgraph.cache_gate import seed_cache_entry

        seed_cache_entry(
            self.cache,
            self.sidecar,
            query=query_key,
            value=tool_result,
            category_slug="fx_rates",
            cache_policy="replay_safe",
        )
        self.session_tool_cache[query_key] = tool_result

    def schedule_turn_digest(self, user_message: str, assistant_response: str, *, turn_id: str) -> None:
        if not self.cortex or not assistant_response.strip():
            return
        payload = f"User: {user_message}\nAssistant: {assistant_response}"
        self.cortex.schedule_digest(payload, source_id=turn_id)
