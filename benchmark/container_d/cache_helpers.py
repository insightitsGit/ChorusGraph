"""Healthcare semantic cache — seed and restore pipeline state (mirror Container F)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from benchmark.healthcare_workload import CASES, PARAPHRASES, HealthcareCase

CLINICAL_SLUG = "clinical_guidelines"


def cache_query_key(case: HealthcareCase) -> str:
    """Cache key includes depth — hop artifacts differ by pipeline depth."""
    return f"{case.presentation}\n[pipeline_depth={case.pipeline_depth}]"


def cache_seed_phrases(case: HealthcareCase) -> List[str]:
    """Canonical + paraphrase phrases for a clinical case (like F CANONICAL_QUERIES)."""
    base_id = case.canonical_id or case.case_id.split("-d")[0]
    phrases: List[str] = []
    for row in CASES:
        if row["case_id"] == base_id:
            p = str(row["presentation"])
            if p and p not in phrases:
                phrases.append(p)
            break
    if not phrases and case.presentation:
        phrases.append(case.presentation)
    for alt in PARAPHRASES.get(base_id, []):
        if alt and alt not in phrases:
            phrases.append(alt)
    return phrases


def build_cache_payload(state: Dict[str, Any], *, response: str = "") -> Dict[str, Any]:
    """Snapshot restorable clinical pipeline state for cache reuse."""
    hop_artifacts = dict(state.get("hop_artifacts") or {})
    return {
        "hop_artifacts": hop_artifacts,
        "retrieved": list(state.get("retrieved") or []),
        "interactions": list(state.get("interactions") or []),
        "drugs": list(state.get("drugs") or []),
        "topic": str(state.get("topic") or ""),
        "abstained": bool(state.get("abstained")),
        "analysis": str(state.get("analysis") or ""),
        "safety_verdict": str(state.get("safety_verdict") or ""),
        "response": response,
    }


def seed_healthcare_cache(
    runtime: Any,
    message: str,
    payload: Dict[str, Any],
    *,
    extra_queries: Optional[List[str]] = None,
    pipeline_depth: Optional[int] = None,
) -> None:
    from chorusgraph.cache_gate import seed_cache_entry

    extra_queries = extra_queries or []
    queries = [message] if message else []
    if pipeline_depth is not None:
        for phrase in list(extra_queries):
            if phrase:
                queries.append(f"{phrase}\n[pipeline_depth={pipeline_depth}]")
    for phrase in extra_queries:
        if phrase and phrase not in queries:
            queries.append(phrase)
    for query_key in queries:
        if not query_key:
            continue
        seed_cache_entry(
            runtime.cache,
            runtime.sidecar,
            query=query_key,
            value=payload,
            category_slug=CLINICAL_SLUG,
            cache_policy="replay_safe",
        )
        runtime.session_tool_cache[query_key] = payload


def cached_response_from_state(state: Dict[str, Any]) -> Optional[str]:
    """Resolved cached answer for cache-hit writer fast path (mirror Container F)."""
    if not state.get("cache_hit"):
        return None
    for key in ("cached_response", "response"):
        raw = state.get(key)
        if raw:
            return str(raw)
    writer_art = (state.get("hop_artifacts") or {}).get("writer") or {}
    if writer_art.get("response"):
        return str(writer_art["response"])
    return None


def apply_cache_payload(update: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Merge cached clinical state into graph update after cache_gate hit."""
    if not isinstance(payload, dict):
        return update
    merged = dict(update)
    merged["hop_artifacts"] = dict(payload.get("hop_artifacts") or {})
    merged["retrieved"] = list(payload.get("retrieved") or [])
    merged["interactions"] = list(payload.get("interactions") or [])
    merged["drugs"] = list(payload.get("drugs") or [])
    merged["topic"] = str(payload.get("topic") or "")
    merged["abstained"] = bool(payload.get("abstained"))
    merged["analysis"] = str(payload.get("analysis") or "")
    merged["safety_verdict"] = str(payload.get("safety_verdict") or "")
    response = str(payload.get("response") or "")
    if response:
        merged["cached_response"] = response
        merged["response"] = response
    return merged
