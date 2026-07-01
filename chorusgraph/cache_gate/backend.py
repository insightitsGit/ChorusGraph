"""Recall candidates from PrismCache without serving (read-only wrapper)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

import numpy as np

from prism.cache import PrismCache
from prism.lib.resonance import WavePacket

from chorusgraph.cache_gate.sidecar import SidecarStore


@dataclass(frozen=True)
class CacheCandidate:
    packet_id: str
    constructive_score: float
    value: Any
    query_text: str
    raw_embedding_384: np.ndarray
    category_slug: str


def recall(
    cache: PrismCache,
    sidecar: SidecarStore,
    *,
    raw_embedding_384: np.ndarray,
    projected_vector_64: np.ndarray,
    top_k: int = 5,
) -> List[CacheCandidate]:
    """
    Stage-1 coarse recall via PrismResonance (64-d), enriched with ChorusGraph sidecar.

    Does not modify PrismCache — uses the same internal resonance store as get_or_call.
    """
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
            # Fallback: re-embed canonical query text (deterministic with same embedder)
            raw_384 = cache._embedder.embed(entry.query_text)
            slug = ""
        else:
            raw_384 = meta.raw_embedding_384
            slug = meta.category_slug
        candidates.append(
            CacheCandidate(
                packet_id=hit.packet_id,
                constructive_score=float(hit.constructive_score),
                value=entry.response,
                query_text=entry.query_text,
                raw_embedding_384=raw_384,
                category_slug=slug,
            )
        )
    return candidates


def seed_cache_entry(
    cache: PrismCache,
    sidecar: SidecarStore,
    *,
    query: str,
    value: Any,
    category_slug: str,
    cache_policy: str,
) -> str:
    """Populate PrismCache + sidecar without invoking an LLM (shadow seeding)."""
    raw = cache._embedder.embed(query)
    envelope = cache._projector.project(raw)
    packet_id = envelope.envelope_id
    cache._store_response(
        packet_id=packet_id,
        query_vector=envelope.vector,
        query_text=query,
        response=value,
        metadata={"category_slug": category_slug, "cache_policy": cache_policy},
    )
    sidecar.put(
        packet_id,
        raw_embedding=raw,
        category_slug=category_slug,
        cache_policy=cache_policy,
        canonical_query=query,
    )
    return packet_id
