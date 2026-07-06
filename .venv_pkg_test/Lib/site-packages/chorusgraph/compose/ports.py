"""Swappable component ports — engine-fixed vs replaceable backends."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, Sequence, runtime_checkable

import numpy as np

from chorusgraph.cache_gate.backend import CacheCandidate
from chorusgraph.sections.models import CacheProfile


@runtime_checkable
class CacheBackend(Protocol):
    """
    Semantic / exact cache port.

    Default: ``PrismCacheBackend`` (PrismCache + SidecarStore).
    Replace with e.g. ``RedisCacheBackend`` for external KV stores.
    """

    name: str
    _chorusgraph_cache_backend: bool

    def embed(self, text: str) -> np.ndarray:
        """384-d query embedding."""

    def project_64(self, raw: np.ndarray) -> np.ndarray:
        """Tenant-seeded 64-d projection (PrismLang JL)."""

    def recall(
        self,
        *,
        raw_embedding_384: np.ndarray,
        projected_vector_64: np.ndarray,
        top_k: int = 5,
        scope_id: str = "global",
        category_slug: Optional[str] = None,
        now: Optional[float] = None,
    ) -> List[CacheCandidate]:
        """Stage-1 coarse recall."""

    def recall_direct(
        self,
        *,
        profile: CacheProfile,
        scope_id: str,
        category_slug: str,
        query: str,
        fingerprint_key: Optional[str] = None,
        now: Optional[float] = None,
    ) -> Optional[CacheCandidate]:
        """Exact / fingerprint lookup."""

    def seed(
        self,
        *,
        query: str,
        value: Any,
        category_slug: str,
        cache_policy: str,
        profile: Optional[CacheProfile] = None,
        scope_id: str = "global",
        fingerprint_key: str = "",
        now: Optional[float] = None,
    ) -> str:
        """Store a cache entry; returns entry id."""


@runtime_checkable
class MemoryBackend(Protocol):
    """L3 memory port — default: PrismCortex via ``CortexMemoryService``."""

    name: str

    def schedule_digest(self, payload: str, *, source_id: str) -> None: ...

    def recall_structured(
        self,
        query: str,
        *,
        cache: Any = None,
        raw_384: Optional[np.ndarray] = None,
    ) -> Any: ...


@runtime_checkable
class ToolBackend(Protocol):
    """Tool execution registry port."""

    name: str

    def get(self, name: str) -> Any: ...

    def list_names(self) -> List[str]: ...


@runtime_checkable
class PersistenceBackend(Protocol):
    """
    Checkpoint + Cortex graph persistence port (5th swappable port).

    Default: SQLite/file JSON (free, single-instance).
    Enterprise: Postgres (license-gated, multi-replica safe).
    """

    name: str

    def make_checkpointer(self, *, checkpoint_root: str) -> Any:
        """Build an ``EngineCheckpointer`` for graph run resume."""

    def make_graph_store(self, *, graph_path: str, tenant_id: str) -> Any:
        """Build a durable Cortex ``GraphStore``."""


@runtime_checkable
class RetrievalBackend(Protocol):
    """
    L2 retrieval port — default: keyword stand-in (zero dependencies).
    Swap for ``PrismRAGRetrievalBackend`` for vector search + taxonomy remap.
    """

    name: str

    def retrieve(self, topic: str, query: str, *, top_k: int = 6) -> List[Dict[str, Any]]:
        """Return ranked chunks: at least {id, topic, text, source, category_slug, score}."""

    def index(self, corpus: Sequence[Dict[str, Any]]) -> None:
        """(Re)build the backend index from {id, topic, text, source} records."""


def is_cache_backend(obj: Any) -> bool:
    return getattr(obj, "_chorusgraph_cache_backend", False) is True


def is_retrieval_backend(obj: Any) -> bool:
    return getattr(obj, "_chorusgraph_retrieval_backend", False) is True


__all__ = [
    "CacheBackend",
    "MemoryBackend",
    "PersistenceBackend",
    "RetrievalBackend",
    "ToolBackend",
    "is_cache_backend",
    "is_retrieval_backend",
]
