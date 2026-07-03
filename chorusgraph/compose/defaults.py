"""Default Prism-family providers for ``ChorusStack``."""

from __future__ import annotations

from typing import Any, Optional

from chorusgraph.cache_gate.sidecar import SidecarStore
from chorusgraph.compose.adapters.memory import CortexMemoryBackend, default_memory_backend
from chorusgraph.compose.adapters.prism_cache import PrismCacheBackend
from chorusgraph.compose.ports import CacheBackend, MemoryBackend
from chorusgraph.ledger.sink import SqliteLedgerSink
from chorusgraph.nodes.tool import ToolRegistry, default_finance_registry
from chorusgraph.policy.embedder_guard import build_guarded_cache


def default_sidecar(path: str = ":memory:") -> SidecarStore:
    return SidecarStore(path)


def default_prism_cache_backend(
    tenant_id: str,
    *,
    sidecar: Optional[SidecarStore] = None,
    embedder: Any = None,
) -> PrismCacheBackend:
    cache = build_guarded_cache(tenant_id, embedder=embedder)
    return PrismCacheBackend(cache, sidecar or default_sidecar())


def default_tool_registry() -> ToolRegistry:
    return default_finance_registry()


def default_checkpointer(root: str = ".chorusgraph/checkpoints"):
    from chorusgraph.core.persistence import json_file_checkpointer

    return json_file_checkpointer(root)


def default_ledger_sink(path: str = ":memory:") -> SqliteLedgerSink:
    return SqliteLedgerSink(path)


__all__ = [
    "default_checkpointer",
    "default_ledger_sink",
    "default_memory_backend",
    "default_prism_cache_backend",
    "default_sidecar",
    "default_tool_registry",
]
