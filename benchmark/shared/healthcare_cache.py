"""Shared healthcare cache seeding with CacheProfile + quality gate (H21)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from chorusgraph.cache_gate import seed_cache_entry
from chorusgraph.cache_gate.scope import scope_id as make_scope_id
from chorusgraph.cache_gate.seed_policy import should_seed_cache
from chorusgraph.sections.models import CachePolicy, CacheProfile, Section
from chorusgraph.sections.profiles import default_registry

CLINICAL_RETRIEVAL_SLUG = "clinical_retrieval"
CLINICAL_GUIDELINES_SLUG = "clinical_guidelines"


def facts_only_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Archetype C — cache mid-pipeline facts, never whole judgment responses."""
    return {
        "retrieved": list(payload.get("retrieved") or []),
        "interactions": list(payload.get("interactions") or []),
        "drugs": list(payload.get("drugs") or []),
        "topic": str(payload.get("topic") or ""),
        "hop_artifacts": {
            k: v
            for k, v in (payload.get("hop_artifacts") or {}).items()
            if k in ("intake", "retrieve", "drug_check")
        },
    }


def seed_clinical_cache_entry(
    runtime: Any,
    *,
    query: str,
    payload: Dict[str, Any],
    category_slug: str = CLINICAL_RETRIEVAL_SLUG,
    profile: Optional[CacheProfile] = None,
    tenant_id: str = "healthcare-benchmark",
    session_id: Optional[str] = None,
    fingerprint_key: str = "",
    response: str = "",
    abstained: bool = False,
    safety_verdict: Any = None,
    trace_fn: Optional[Any] = None,
) -> bool:
    """
    Quality-gated seed into shared runtime cache. Returns True if seeded.
    """
    registry = default_registry()
    profile = profile or registry.get(category_slug)
    allowed, reason = should_seed_cache(
        response=response,
        abstained=abstained,
        safety_verdict=safety_verdict,
        require_safety=(profile.risk_tier == "high"),
    )
    if not allowed:
        if trace_fn:
            trace_fn("cache_seed_refused", reason=reason, category_slug=category_slug)
        return False

    facts = facts_only_payload(payload)
    sid = make_scope_id(
        profile.scope,
        tenant_id=tenant_id,
        session_id=session_id,
    )
    seed_cache_entry(
        runtime.cache,
        runtime.sidecar,
        query=query,
        value=facts,
        category_slug=category_slug,
        cache_policy=CachePolicy.REPLAY_SAFE.value,
        profile=profile,
        scope_id=sid,
        fingerprint_key=fingerprint_key,
    )
    runtime.session_tool_cache[query] = facts
    if fingerprint_key:
        runtime.session_tool_cache[fingerprint_key] = facts
    return True


def gate_clinical(
    runtime: Any,
    *,
    query: str,
    category_slug: str = CLINICAL_RETRIEVAL_SLUG,
    profile: Optional[CacheProfile] = None,
    tenant_id: str = "healthcare-benchmark",
    session_id: Optional[str] = None,
    fingerprint_key: Optional[str] = None,
    coarse_threshold: float = 0.88,
    verify_threshold: float = 0.95,
    raw_embedding_384=None,
    projected_vector_64=None,
):
    from chorusgraph.cache_gate import gate

    registry = default_registry()
    profile = profile or registry.get(category_slug)
    section = Section(
        section_id="clinical_lookup",
        category_slug=category_slug,
        content=query,
        cache_policy=CachePolicy.REPLAY_SAFE,
    )
    return gate(
        query,
        section,
        runtime.cache,
        runtime.sidecar,
        coarse_threshold=coarse_threshold,
        verify_threshold=verify_threshold,
        profile=profile,
        fingerprint_key=fingerprint_key,
        tenant_id=tenant_id,
        session_id=session_id,
        raw_embedding_384=raw_embedding_384,
        projected_vector_64=projected_vector_64,
    )


__all__ = [
    "CLINICAL_GUIDELINES_SLUG",
    "CLINICAL_RETRIEVAL_SLUG",
    "facts_only_payload",
    "gate_clinical",
    "seed_clinical_cache_entry",
]
