"""Two-stage cache gate — ADR-002 core algorithm."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import numpy as np

from chorusgraph.cache_gate.backend import recall
from chorusgraph.cache_gate.decision import Decision, DecisionKind
from chorusgraph.sections.models import CachePolicy, Section

if TYPE_CHECKING:
    from prism.cache import PrismCache

    from chorusgraph.cache_gate.sidecar import SidecarStore


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32).ravel()
    b = np.asarray(b, dtype=np.float32).ravel()
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-12:
        return 0.0
    return float(np.dot(a, b) / denom)


def gate(
    query: str,
    section: Section,
    cache: "PrismCache",
    sidecar: "SidecarStore",
    *,
    coarse_threshold: float = 0.88,
    verify_threshold: float = 0.95,
    top_k: int = 5,
    raw_embedding_384: Optional[np.ndarray] = None,
    projected_vector_64: Optional[np.ndarray] = None,
) -> Decision:
    """
    Two-stage cache gate per Handoff 2 §5 / DESIGN §8.1.

    Stage 0: policy skip
    Stage 1: 64-d coarse recall (PrismCache / PrismResonance)
    Stage 2: 384-d full-precision verify (pre-projection cosine)
    Stage 3: policy-gated reuse decision
    """
    # Stage 0 — policy
    if section.cache_policy == CachePolicy.NO_CACHE:
        return Decision(kind=DecisionKind.MISS)

    # Stage 1 — coarse recall (reuse ingress embedding when provided)
    if raw_embedding_384 is None:
        raw = cache._embedder.embed(query)
    else:
        raw = np.asarray(raw_embedding_384, dtype=np.float32).ravel()
    if projected_vector_64 is None:
        envelope = cache._projector.project(raw)
        projected = np.asarray(envelope.vector, dtype=np.float32)
    else:
        projected = np.asarray(projected_vector_64, dtype=np.float32).ravel()

    candidates = recall(
        cache,
        sidecar,
        raw_embedding_384=raw,
        projected_vector_64=projected,
        top_k=top_k,
    )
    top = candidates[0] if candidates else None
    if top is None or top.constructive_score < coarse_threshold:
        return Decision(
            kind=DecisionKind.MISS,
            coarse_score=top.constructive_score if top else 0.0,
        )

    # Taxonomy guard — cross-category block
    if top.category_slug and section.category_slug and top.category_slug != section.category_slug:
        return Decision(
            kind=DecisionKind.MISS,
            coarse_score=top.constructive_score,
            candidate_query=top.query_text,
            candidate_packet_id=top.packet_id,
        )

    # Stage 2 — full-precision verify on 384-d (NOT 64-d projection)
    verify = cosine_similarity(raw, top.raw_embedding_384)
    if verify < verify_threshold:
        return Decision(
            kind=DecisionKind.MISS,
            coarse_score=top.constructive_score,
            verify_score=verify,
            candidate_query=top.query_text,
            candidate_packet_id=top.packet_id,
        )

    # Stage 3 — policy-gated reuse
    if section.cache_policy == CachePolicy.EXACT:
        kind = DecisionKind.HIT_REUSE
    elif section.cache_policy == CachePolicy.REPLAY_SAFE:
        kind = DecisionKind.HIT_REVALIDATE
    elif section.cache_policy == CachePolicy.SEMANTIC:
        kind = DecisionKind.HIT_AS_CONTEXT
    else:
        return Decision(kind=DecisionKind.MISS)

    return Decision(
        kind=kind,
        value=top.value,
        coarse_score=top.constructive_score,
        verify_score=verify,
        candidate_query=top.query_text,
        candidate_packet_id=top.packet_id,
    )
