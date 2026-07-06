"""Redis (or in-memory) exact cache — external ``CacheBackend`` example."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, List, Optional

import numpy as np

from chorusgraph.cache_gate.backend import CacheCandidate
from chorusgraph.cache_gate.scope import normalize_exact_query
from chorusgraph.sections.models import CacheProfile
from chorusgraph.policy.embedder_guard import build_guarded_cache
from chorusgraph.compose.adapters.prism_cache import PrismCacheBackend


def _memory_store() -> dict[str, str]:
    return {}


class RedisCacheBackend:
    """
    External cache backend using Redis when available, else an in-process dict.

    Semantic recall delegates to a nested ``PrismCacheBackend`` built from a
    tenant-scoped in-memory PrismCache (coarse path). Exact/fingerprint keys
    live in Redis — demonstrating swap of the durable store while keeping
    PrismLang projection on the engine hot path.
    """

    name = "redis"
    _chorusgraph_cache_backend = True

    def __init__(
        self,
        *,
        tenant_id: str = "default",
        redis_url: Optional[str] = None,
        prefix: str = "chorusgraph:cache",
    ) -> None:
        self.tenant_id = tenant_id
        self.prefix = prefix
        self._redis = None
        self._memory = _memory_store()
        if redis_url:
            try:
                import redis  # type: ignore[import-untyped]

                self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None

        from chorusgraph.cache_gate.sidecar import SidecarStore

        prism_cache = build_guarded_cache(tenant_id)
        sidecar = SidecarStore(":memory:")
        self._semantic = PrismCacheBackend(prism_cache, sidecar)

    def _key(self, scope_id: str, category_slug: str, query: str) -> str:
        digest = hashlib.sha256(normalize_exact_query(query).encode()).hexdigest()[:24]
        return f"{self.prefix}:{self.tenant_id}:{scope_id}:{category_slug}:{digest}"

    def _get_raw(self, key: str) -> Optional[Any]:
        if self._redis is not None:
            raw = self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        return json.loads(self._memory[key]) if key in self._memory else None

    def _set_raw(self, key: str, value: Any) -> None:
        payload = json.dumps(value, default=str)
        if self._redis is not None:
            self._redis.set(key, payload)
        else:
            self._memory[key] = payload

    def embed(self, text: str) -> np.ndarray:
        return self._semantic.embed(text)

    def project_64(self, raw: np.ndarray) -> np.ndarray:
        return self._semantic.project_64(raw)

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
        return self._semantic.recall(
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
        now = time.time() if now is None else now
        if profile.keying == "fingerprint" and not fingerprint_key:
            return None
        canonical = fingerprint_key if profile.keying == "fingerprint" else normalize_exact_query(query)
        key = self._key(scope_id, category_slug, canonical)
        value = self._get_raw(key)
        if value is None:
            return None
        if profile.ttl_s is not None:
            stored_at = float(value.get("_stored_at", 0))
            if now - stored_at > profile.ttl_s:
                return None
        raw = self.embed(query if profile.keying != "fingerprint" else (fingerprint_key or query))
        return CacheCandidate(
            packet_id=key,
            constructive_score=1.0,
            value=value.get("payload"),
            query_text=query,
            raw_embedding_384=raw,
            category_slug=category_slug,
            scope_id=scope_id,
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
        profile = profile or CacheProfile()
        now = time.time() if now is None else now
        if profile.keying in ("exact", "fingerprint"):
            canonical = fingerprint_key if profile.keying == "fingerprint" else normalize_exact_query(query)
            key = self._key(scope_id, category_slug, canonical)
            self._set_raw(
                key,
                {
                    "payload": value,
                    "_stored_at": now,
                    "cache_policy": cache_policy,
                    "category_slug": category_slug,
                },
            )
            return key
        return self._semantic.seed(
            query=query,
            value=value,
            category_slug=category_slug,
            cache_policy=cache_policy,
            profile=profile,
            scope_id=scope_id,
            fingerprint_key=fingerprint_key,
            now=now,
        )


__all__ = ["RedisCacheBackend"]
