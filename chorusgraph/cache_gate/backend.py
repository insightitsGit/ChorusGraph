"""Recall candidates from PrismCache without serving (read-only wrapper)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, List, Optional

import numpy as np

from prism.cache import PrismCache
from prism.lib.resonance import WavePacket

from chorusgraph.cache_gate.scope import normalize_exact_query
from chorusgraph.cache_gate.sidecar import SidecarEntry, SidecarStore
from chorusgraph.sections.models import CacheProfile


@dataclass(frozen=True)
class CacheCandidate:
    packet_id: str
    constructive_score: float
    value: Any
    query_text: str
    raw_embedding_384: np.ndarray
    category_slug: str
    scope_id: str = "global"
    # prismlib-plus ≥0.8.0 CacheEntry.created_at when available
    created_at: Optional[float] = None


def _load_entry(cache: PrismCache, packet_id: str) -> Any:
    entry = cache._store.load(packet_id)
    if entry is None or entry.is_expired():
        return None
    return entry


def _load_value(cache: PrismCache, packet_id: str) -> Any:
    entry = _load_entry(cache, packet_id)
    if entry is None:
        return None
    return entry.response


def _entry_to_candidate(
    cache: PrismCache,
    meta: SidecarEntry,
    *,
    score: float = 1.0,
) -> Optional[CacheCandidate]:
    entry = _load_entry(cache, meta.packet_id)
    if entry is None:
        return None
    created = getattr(entry, "created_at", None)
    return CacheCandidate(
        packet_id=meta.packet_id,
        constructive_score=score,
        value=entry.response,
        query_text=meta.canonical_query,
        raw_embedding_384=meta.raw_embedding_384,
        category_slug=meta.category_slug,
        scope_id=meta.scope_id,
        created_at=float(created) if created is not None else None,
    )


def recall(
    cache: PrismCache,
    sidecar: SidecarStore,
    *,
    raw_embedding_384: np.ndarray,
    projected_vector_64: np.ndarray,
    top_k: int = 5,
    scope_id: str = "global",
    category_slug: Optional[str] = None,
    now: Optional[float] = None,
) -> List[CacheCandidate]:
    """
    Stage-1 coarse recall via PrismResonance (64-d), enriched with ChorusGraph sidecar.

    Filters candidates to matching scope_id and non-expired sidecar TTL.
    """
    now = time.time() if now is None else now
    query_packet = WavePacket.from_real_vector(
        projected_vector_64.astype(np.float32),
        phase_state=cache._cfg.phase_state,
    )
    hits = cache._resonance.query(
        query_packet,
        top_k=top_k,
        amplitude_min=0.001,
    )

    candidates: list[CacheCandidate] = []
    for hit in hits:
        entry = cache._store.load(hit.packet_id)
        if entry is None or entry.is_expired():
            continue
        meta = sidecar.get(hit.packet_id)
        if meta is None:
            raw_384 = cache._embedder.embed(entry.query_text)
            slug = ""
            sid = "global"
        else:
            if meta.scope_id != scope_id:
                continue
            if category_slug and meta.category_slug != category_slug:
                continue
            if sidecar.is_expired(meta, now=now):
                continue
            raw_384 = meta.raw_embedding_384
            slug = meta.category_slug
            sid = meta.scope_id
        created = getattr(entry, "created_at", None)
        candidates.append(
            CacheCandidate(
                packet_id=hit.packet_id,
                constructive_score=float(hit.constructive_score),
                value=entry.response,
                query_text=entry.query_text,
                raw_embedding_384=raw_384,
                category_slug=slug,
                scope_id=sid,
                created_at=float(created) if created is not None else None,
            )
        )
    return candidates


def recall_direct(
    cache: PrismCache,
    sidecar: SidecarStore,
    *,
    profile: CacheProfile,
    scope_id: str,
    category_slug: str,
    query: str,
    fingerprint_key: Optional[str] = None,
    now: Optional[float] = None,
) -> Optional[CacheCandidate]:
    """Exact or fingerprint lookup — no semantic resonance."""
    now = time.time() if now is None else now
    meta: Optional[SidecarEntry] = None
    if profile.keying == "fingerprint":
        if not fingerprint_key:
            return None
        meta = sidecar.find_by_fingerprint(
            scope_id=scope_id,
            category_slug=category_slug,
            fingerprint_key=fingerprint_key,
            now=now,
        )
    elif profile.keying == "exact":
        meta = sidecar.find_by_exact(
            scope_id=scope_id,
            category_slug=category_slug,
            query=normalize_exact_query(query),
            now=now,
        )
    else:
        return None
    if meta is None:
        return None
    return _entry_to_candidate(cache, meta, score=1.0)


def _seed_prism_cache_entry(
    cache: PrismCache,
    sidecar: SidecarStore,
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
    """Populate PrismCache + sidecar without invoking an LLM (shadow seeding)."""
    profile = profile or CacheProfile()
    now = time.time() if now is None else now
    keying = profile.keying
    canonical = normalize_exact_query(query) if keying == "exact" else query
    valid_until = (now + profile.ttl_s) if profile.ttl_s else None

    if keying in ("fingerprint", "exact"):
        raw = cache._embedder.embed(fingerprint_key or canonical)
    else:
        raw = cache._embedder.embed(query)
    envelope = cache._projector.project(raw)
    packet_id = envelope.envelope_id
    cache._store_response(
        packet_id=packet_id,
        query_vector=envelope.vector,
        query_text=query,
        response=value,
        metadata={
            "category_slug": category_slug,
            "cache_policy": cache_policy,
            "scope_id": scope_id,
            "keying": keying,
        },
    )
    sidecar.put(
        packet_id,
        raw_embedding=raw,
        category_slug=category_slug,
        cache_policy=cache_policy,
        canonical_query=canonical,
        scope_id=scope_id,
        keying=keying,
        fingerprint_key=fingerprint_key,
        valid_from=now,
        valid_until=valid_until,
    )
    return packet_id


def seed_cache_entry(
    cache: Any,
    sidecar: "SidecarStore | None",
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
    """Populate cache via ``CacheBackend`` (Prism default or external)."""
    from chorusgraph.compose.ports import is_cache_backend

    if is_cache_backend(cache):
        return cache.seed(
            query=query,
            value=value,
            category_slug=category_slug,
            cache_policy=cache_policy,
            profile=profile,
            scope_id=scope_id,
            fingerprint_key=fingerprint_key,
            now=now,
        )
    if sidecar is None:
        raise TypeError("sidecar is required when cache is a PrismCache instance")
    return _seed_prism_cache_entry(
        cache,
        sidecar,
        query=query,
        value=value,
        category_slug=category_slug,
        cache_policy=cache_policy,
        profile=profile,
        scope_id=scope_id,
        fingerprint_key=fingerprint_key,
        now=now,
    )


__all__ = ["CacheCandidate", "recall", "recall_direct", "seed_cache_entry"]
