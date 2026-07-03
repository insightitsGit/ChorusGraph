"""Healthcare semantic cache — seed and restore pipeline state (mirror FC2)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from benchmark.healthcare.cases import CASES, PARAPHRASES
from benchmark.healthcare_workload import HealthcareCase
from benchmark.shared.corpus_seed import (
    healthcare_cache_query_key,
    healthcare_seed_phrases,
    seed_healthcare_clinical_cache,
)

CLINICAL_SLUG = "clinical_guidelines"


def cache_query_key(case: HealthcareCase) -> str:
    """Cache key includes depth — hop artifacts differ by pipeline depth."""
    return healthcare_cache_query_key(case.presentation, pipeline_depth=case.pipeline_depth)


def cache_seed_phrases(case: HealthcareCase) -> List[str]:
    """Canonical + paraphrase phrases for a clinical case (H10 multi-phrase pattern)."""
    return healthcare_seed_phrases(
        case_id=case.case_id,
        presentation=case.presentation,
        canonical_id=case.canonical_id,
    )


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
    if pipeline_depth is None:
        raise ValueError("pipeline_depth required for healthcare cache seed")
    seed_healthcare_clinical_cache(
        runtime,
        presentation=message,
        pipeline_depth=pipeline_depth,
        payload=payload,
        seed_phrases=extra_queries or [],
        category_slug=CLINICAL_SLUG,
    )


def cached_response_from_state(state: Dict[str, Any]) -> Optional[str]:
    """Resolved cached answer for cache-hit writer fast path (mirror FC2)."""
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


__all__ = [
    "CASES",
    "PARAPHRASES",
    "CLINICAL_SLUG",
    "apply_cache_payload",
    "build_cache_payload",
    "cache_query_key",
    "cache_seed_phrases",
    "cached_response_from_state",
    "seed_healthcare_cache",
]
