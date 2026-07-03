"""PrismCache + SidecarStore — default ChorusGraph cache backend."""

from __future__ import annotations

from typing import Any, List, Optional

import numpy as np

from chorusgraph.cache_gate import backend as cache_backend
from chorusgraph.cache_gate.backend import CacheCandidate
from chorusgraph.cache_gate.sidecar import SidecarStore
from chorusgraph.sections.models import CacheProfile


class PrismCacheBackend:
    """Wraps PrismCache + SidecarStore as a ``CacheBackend`` port."""

    name = "prism"
    _chorusgraph_cache_backend = True

    def __init__(self, cache: Any, sidecar: SidecarStore) -> None:
        self.cache = cache
        self.sidecar = sidecar

    def embed(self, text: str) -> np.ndarray:
        return np.asarray(self.cache._embedder.embed(text), dtype=np.float32).ravel()

    def project_64(self, raw: np.ndarray) -> np.ndarray:
        envelope = self.cache._projector.project(np.asarray(raw, dtype=np.float32).ravel())
        return np.asarray(envelope.vector, dtype=np.float32).ravel()

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
        return cache_backend.recall(
            self.cache,
            self.sidecar,
            raw_embedding_384=raw_embedding_384,
            projected_vector_64=projected_vector_64,
            top_k=top_k,
            scope_id=scope_id,
            category_slug=category_slug,
            now=now,
        )

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
        return cache_backend.recall_direct(
            self.cache,
            self.sidecar,
            profile=profile,
            scope_id=scope_id,
            category_slug=category_slug,
            query=query,
            fingerprint_key=fingerprint_key,
            now=now,
        )

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
        return cache_backend._seed_prism_cache_entry(
            self.cache,
            self.sidecar,
            query=query,
            value=value,
            category_slug=category_slug,
            cache_policy=cache_policy,
            profile=profile,
            scope_id=scope_id,
            fingerprint_key=fingerprint_key,
            now=now,
        )


__all__ = ["PrismCacheBackend"]
