"""Composable product stack — engine + swappable section backends."""

from chorusgraph.compose.adapters.memory import CortexMemoryBackend
from chorusgraph.compose.adapters.prism_cache import PrismCacheBackend
from chorusgraph.compose.adapters.redis_cache import RedisCacheBackend
from chorusgraph.compose.defaults import (
    default_checkpointer,
    default_ledger_sink,
    default_memory_backend,
    default_prism_cache_backend,
    default_sidecar,
    default_tool_registry,
)
from chorusgraph.compose.ports import CacheBackend, MemoryBackend, ToolBackend, is_cache_backend
from chorusgraph.compose.stack import ChorusStack

__all__ = [
    "CacheBackend",
    "ChorusStack",
    "CortexMemoryBackend",
    "MemoryBackend",
    "PrismCacheBackend",
    "RedisCacheBackend",
    "ToolBackend",
    "default_checkpointer",
    "default_ledger_sink",
    "default_memory_backend",
    "default_prism_cache_backend",
    "default_sidecar",
    "default_tool_registry",
    "is_cache_backend",
]
