"""HC1 single-agent clinical cache — seed and restore (mirror FC1 / HC2)."""

from __future__ import annotations

from typing import Any, Dict, List

from benchmark.hc2.cache_helpers import (
    CLINICAL_SLUG,
    apply_cache_payload,
    cache_query_key,
    cache_seed_phrases,
    cached_response_from_state,
    seed_healthcare_cache,
)
from benchmark.healthcare_workload import HealthcareCase


def build_hc1_cache_payload(view: Dict[str, Any], *, response: str) -> Dict[str, Any]:
    """Snapshot restorable single-agent clinical state for cache reuse."""
    case: HealthcareCase = view["case"]
    return {
        "retrieved": list(view.get("retrieved") or []),
        "interactions": list(view.get("interactions") or []),
        "drugs": list(case.drugs),
        "topic": str(case.topic),
        "abstained": bool(view.get("abstained")),
        "response": response,
    }


__all__ = [
    "CLINICAL_SLUG",
    "apply_cache_payload",
    "build_hc1_cache_payload",
    "cache_query_key",
    "cache_seed_phrases",
    "cached_response_from_state",
    "seed_healthcare_cache",
]
