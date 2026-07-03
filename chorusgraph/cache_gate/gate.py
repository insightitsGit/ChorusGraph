"""Two-stage cache gate — ADR-002 core algorithm + CacheProfile (H21)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

import numpy as np

from chorusgraph.cache_gate.backend import recall, recall_direct
from chorusgraph.cache_gate.decision import Decision, DecisionKind
from chorusgraph.cache_gate.scope import scope_id as make_scope_id
from chorusgraph.sections.models import CachePolicy, CacheProfile, Section
from chorusgraph.sections.profiles import default_registry

if TYPE_CHECKING:
    from prism.cache import PrismCache

    from chorusgraph.cache_gate.sidecar import SidecarStore

# Stricter verify for high-risk clinical judgment (measured operating point + margin).
HIGH_RISK_VERIFY_DEFAULT = 0.97


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32).ravel()
    b = np.asarray(b, dtype=np.float32).ravel()
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-12:
        return 0.0
    return float(np.dot(a, b) / denom)


def _verify_threshold_for(profile: CacheProfile, verify_threshold: float) -> float:
    if profile.risk_tier == "high":
        return max(verify_threshold, HIGH_RISK_VERIFY_DEFAULT)
    return verify_threshold


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
    profile: Optional[CacheProfile] = None,
    scope_id: Optional[str] = None,
    fingerprint_key: Optional[str] = None,
    tenant_id: str = "default",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    now: Optional[float] = None,
) -> Decision:
    """
    Two-stage cache gate per Handoff 2 §5 / CACHE_PROFILES.md.

    When profile.keying is fingerprint or exact, uses direct lookup (no semantic path).
    """
    now = time.time() if now is None else now
    profile = profile or default_registry().get(section.category_slug)
    sid = scope_id or make_scope_id(
        profile.scope,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
    )
    v_threshold = _verify_threshold_for(profile, verify_threshold)

    if section.cache_policy == CachePolicy.NO_CACHE:
        return Decision(kind=DecisionKind.MISS)

    # Direct keying paths
    if profile.keying in ("fingerprint", "exact"):
        direct = recall_direct(
            cache,
            sidecar,
            profile=profile,
            scope_id=sid,
            category_slug=section.category_slug,
            query=query,
            fingerprint_key=fingerprint_key,
            now=now,
        )
        if direct is None:
            return Decision(kind=DecisionKind.MISS)
        return _decision_from_candidate(direct, section, verify_score=1.0)

    # Semantic two-stage path
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
        scope_id=sid,
        category_slug=section.category_slug,
        now=now,
    )
    top = candidates[0] if candidates else None
    if top is None or top.constructive_score < coarse_threshold:
        return Decision(
            kind=DecisionKind.MISS,
            coarse_score=top.constructive_score if top else 0.0,
        )

    if top.category_slug and section.category_slug and top.category_slug != section.category_slug:
        return Decision(
            kind=DecisionKind.MISS,
            coarse_score=top.constructive_score,
            candidate_query=top.query_text,
            candidate_packet_id=top.packet_id,
        )

    verify = cosine_similarity(raw, top.raw_embedding_384)
    if verify < v_threshold:
        return Decision(
            kind=DecisionKind.MISS,
            coarse_score=top.constructive_score,
            verify_score=verify,
            candidate_query=top.query_text,
            candidate_packet_id=top.packet_id,
        )

    return _decision_from_candidate(top, section, verify_score=verify)


def _decision_from_candidate(top, section: Section, *, verify_score: float) -> Decision:
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
        verify_score=verify_score,
        candidate_query=top.query_text,
        candidate_packet_id=top.packet_id,
    )


__all__ = ["HIGH_RISK_VERIFY_DEFAULT", "cosine_similarity", "gate"]
