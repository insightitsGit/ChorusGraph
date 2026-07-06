"""Composable product stack — engine + swappable section backends."""

from chorusgraph.compose.adapters.memory import CortexMemoryBackend
from chorusgraph.compose.adapters.keyword_retrieval import KeywordRetrievalBackend
from chorusgraph.compose.adapters.prism_cache import PrismCacheBackend
from chorusgraph.compose.adapters.prismrag_retrieval import PrismRAGRetrievalBackend
from chorusgraph.compose.adapters.redis_cache import RedisCacheBackend
from chorusgraph.compose.defaults import (
    default_checkpointer,
    default_ledger_sink,
    default_memory_backend,
    default_prism_cache_backend,
    default_retrieval_backend,
    default_sidecar,
    default_tool_registry,
)
from chorusgraph.compose.ports import (
    CacheBackend,
    MemoryBackend,
    PersistenceBackend,
    RetrievalBackend,
    ToolBackend,
    is_cache_backend,
    is_retrieval_backend,
)
from chorusgraph.compose.adapters.persistence import (
    PostgresPersistenceBackend,
    SqlitePersistenceBackend,
)
from chorusgraph.compose.stack import ChorusStack

__all__ = [
    "CacheBackend",
    "ChorusStack",
    "CortexMemoryBackend",
    "KeywordRetrievalBackend",
    "MemoryBackend",
    "PrismCacheBackend",
    "PostgresPersistenceBackend",
    "PrismRAGRetrievalBackend",
    "RedisCacheBackend",
    "PersistenceBackend",
    "RetrievalBackend",
    "SqlitePersistenceBackend",
    "ToolBackend",
    "default_checkpointer",
    "default_ledger_sink",
    "default_memory_backend",
    "default_prism_cache_backend",
    "default_retrieval_backend",
    "default_sidecar",
    "default_tool_registry",
    "is_cache_backend",
    "is_retrieval_backend",
]
