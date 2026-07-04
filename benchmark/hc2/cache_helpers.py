"""Healthcare semantic cache — facts-only seed/restore (H21 archetype C)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from benchmark.healthcare.cases import CASES, PARAPHRASES
from benchmark.healthcare.fingerprint import clinical_fingerprint, clinical_fingerprint_from_case
from benchmark.healthcare_workload import HealthcareCase
from benchmark.shared.corpus_seed import healthcare_seed_phrases
from benchmark.shared.healthcare_cache import (
    CLINICAL_RETRIEVAL_SLUG,
    facts_only_payload,
    gate_clinical,
    seed_clinical_cache_entry,
)
from chorusgraph.sections.profiles import default_registry

CLINICAL_SLUG = CLINICAL_RETRIEVAL_SLUG


def cache_query_key(case: HealthcareCase) -> str:
    """Semantic lookup key — topic + canonical presentation."""
    return f"{case.topic}:{case.canonical_id or case.case_id}"


def cache_semantic_gate_query(case: HealthcareCase) -> str:
    """Depth-scoped semantic gate key — prevents d6 hits on intake-only d2 seeds."""
    return cache_query_key_from_parts(cache_query_key(case), case.pipeline_depth)


def hop_artifact_has_content(hop_artifacts: Dict[str, Any], key: str) -> bool:
    """True when a hop artifact carries usable content (empty JSON dict does not count)."""
    art = hop_artifacts.get(key)
    if not isinstance(art, dict) or not art:
        return False
    if key == "analyze":
        return bool(str(art.get("reasoning") or "").strip())
    if key == "retrieve":
        return bool(art.get("cited_ids") or str(art.get("summary") or "").strip())
    if key == "intake":
        return bool(str(art.get("facts") or "").strip())
    return bool(art)


def cache_payload_sufficient(payload: Dict[str, Any], pipeline_depth: int) -> bool:
    """Reject semantic hits whose cached facts cannot support the current pipeline depth."""
    facts = facts_only_payload(payload) if isinstance(payload, dict) else {}
    hop = facts.get("hop_artifacts") or {}
    retrieved = facts.get("retrieved") or []
    has_retrieve = bool(hop.get("retrieve") or retrieved)
    has_intake = bool(hop.get("intake"))
    if pipeline_depth >= 4:
        return has_retrieve
    if pipeline_depth >= 2:
        return has_intake
    return True


def cache_fingerprint_key(state: Dict[str, Any], case: HealthcareCase) -> str:
    hop = dict(state.get("hop_artifacts") or {})
    intake = hop.get("intake") or {
        "drugs": list(case.drugs),
        "topic": case.topic,
        "facts": case.presentation[:200],
    }
    retrieved = list(state.get("retrieved") or [])
    if hop.get("retrieve") and not hop["retrieve"].get("cited_ids"):
        hop = dict(hop)
        hop["retrieve"] = {
            **hop["retrieve"],
            "cited_ids": [str(d.get("id") or "") for d in retrieved if d.get("id")],
        }
    return clinical_fingerprint(
        intake,
        pipeline_depth=case.pipeline_depth,
        drugs=case.drugs,
        topic=case.topic,
        hop_artifacts=hop,
        retrieved=retrieved,
        gate_phase=False,
    )


def cache_fingerprint_key_gate(case: HealthcareCase) -> str:
    """Gate-time fingerprint (case metadata only)."""
    return clinical_fingerprint_from_case(case)


def cache_seed_phrases(case: HealthcareCase) -> List[str]:
    return healthcare_seed_phrases(
        case_id=case.case_id,
        presentation=case.presentation,
        canonical_id=case.canonical_id,
    )


def build_cache_payload(state: Dict[str, Any], *, response: str = "") -> Dict[str, Any]:
    """Facts snapshot for cache — response kept for seed policy check only."""
    case = state.get("case")
    payload = {
        "hop_artifacts": dict(state.get("hop_artifacts") or {}),
        "retrieved": list(state.get("retrieved") or []),
        "interactions": list(state.get("interactions") or []),
        "drugs": list(state.get("drugs") or (getattr(case, "drugs", None) or [])),
        "topic": str(state.get("topic") or (getattr(case, "topic", None) or "")),
        "abstained": bool(state.get("abstained")),
        "analysis": str(state.get("analysis") or ""),
        "safety_verdict": state.get("hop_artifacts", {}).get("safety") or state.get("safety_verdict"),
        "response": response,
    }
    return payload


def seed_healthcare_cache(
    runtime: Any,
    message: str,
    payload: Dict[str, Any],
    *,
    extra_queries: Optional[List[str]] = None,
    pipeline_depth: Optional[int] = None,
    session_id: Optional[str] = None,
    fingerprint_key: str = "",
    case: Optional[HealthcareCase] = None,
    trace_fn: Optional[Any] = None,
) -> None:
    if pipeline_depth is None:
        raise ValueError("pipeline_depth required for healthcare cache seed")
    response = str(payload.get("response") or "")
    abstained = bool(payload.get("abstained"))
    safety = payload.get("safety_verdict")
    facts = facts_only_payload(payload)

    queries: List[str] = []
    if message:
        queries.append(message)
    depth_key = cache_query_key_from_parts(message, pipeline_depth)
    if depth_key and depth_key not in queries:
        queries.append(depth_key)
    for phrase in extra_queries or []:
        if phrase and phrase not in queries:
            queries.append(phrase)
        depth_key = cache_query_key_from_parts(phrase, pipeline_depth)
        if depth_key not in queries:
            queries.append(depth_key)

    for query_key in queries:
        seed_clinical_cache_entry(
            runtime,
            query=query_key,
            payload=facts,
            category_slug=CLINICAL_RETRIEVAL_SLUG,
            session_id=session_id,
            fingerprint_key="",
            response=response,
            abstained=abstained,
            safety_verdict=safety,
            trace_fn=trace_fn,
        )

    if fingerprint_key:
        seed_clinical_cache_entry(
            runtime,
            query=fingerprint_key,
            payload=facts,
            category_slug="clinical_judgment",
            profile=default_registry().get("clinical_judgment"),
            session_id=session_id,
            fingerprint_key=fingerprint_key,
            response=response,
            abstained=abstained,
            safety_verdict=safety,
            trace_fn=trace_fn,
        )
        if case is not None:
            gate_fp = clinical_fingerprint_from_case(case)
            if gate_fp != fingerprint_key:
                seed_clinical_cache_entry(
                    runtime,
                    query=gate_fp,
                    payload=facts,
                    category_slug="clinical_judgment",
                    profile=default_registry().get("clinical_judgment"),
                    session_id=session_id,
                    fingerprint_key=gate_fp,
                    response=response,
                    abstained=abstained,
                    safety_verdict=safety,
                    trace_fn=trace_fn,
                )


def cache_query_key_from_parts(presentation: str, pipeline_depth: int) -> str:
    return f"{presentation}\n[pipeline_depth={pipeline_depth}]"


def cached_response_from_state(state: Dict[str, Any]) -> Optional[str]:
    """Judgment responses are not replayed from cache (archetype C)."""
    return None


def first_judgment_hop_after_cache(state: Dict[str, Any], agents: List[str]) -> str:
    """
    After a facts cache hit, skip fact hops and enter at the first judgment hop to (re)run.

    Archetype C: cached facts = intake/retrieve/drug_check only; analyze/safety/writer stay fresh.
    """
    case = state.get("case")
    depth = int(getattr(case, "pipeline_depth", 0) or 0)
    hop = dict(state.get("hop_artifacts") or {})

    if depth >= 6:
        if "analyze" in agents and not hop_artifact_has_content(hop, "analyze"):
            return "analyze"
        if "safety" in agents:
            return "safety"
    if depth >= 4 and "analyze" in agents:
        return "analyze"
    if "writer" in agents:
        return "writer"
    return agents[0]


def apply_cache_payload(update: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Merge cached clinical facts — never replay writer response."""
    if not isinstance(payload, dict):
        return update
    facts = facts_only_payload(payload)
    merged = dict(update)
    merged["hop_artifacts"] = dict(facts.get("hop_artifacts") or {})
    merged["retrieved"] = list(facts.get("retrieved") or [])
    merged["interactions"] = list(facts.get("interactions") or [])
    merged["drugs"] = list(facts.get("drugs") or [])
    merged["topic"] = str(facts.get("topic") or "")
    merged["cache_facts"] = True
    return merged


__all__ = [
    "CASES",
    "PARAPHRASES",
    "CLINICAL_SLUG",
    "apply_cache_payload",
    "build_cache_payload",
    "cache_fingerprint_key",
    "cache_fingerprint_key_gate",
    "cache_payload_sufficient",
    "cache_query_key",
    "cache_semantic_gate_query",
    "cache_seed_phrases",
    "hop_artifact_has_content",
    "cached_response_from_state",
    "first_judgment_hop_after_cache",
    "gate_clinical",
    "seed_healthcare_cache",
]
