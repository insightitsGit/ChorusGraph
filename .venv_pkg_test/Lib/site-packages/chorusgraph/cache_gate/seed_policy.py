"""Quality-gated cache seeding — risk_tier=high (CACHE_PROFILES.md §5)."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

_REFUSAL_PATTERNS = (
    r"cannot provide a recommendation",
    r"safety verdict is missing",
    r"upstream safety verdict",
    r"insufficient grounded evidence",
    r"must abstain",
    r"unable to provide",
)


def is_refusal_response(text: str) -> bool:
    lower = (text or "").lower()
    return any(re.search(p, lower) for p in _REFUSAL_PATTERNS)


def safety_approving(safety_verdict: Any) -> bool:
    if safety_verdict is None:
        return False
    if isinstance(safety_verdict, dict):
        verdict = str(safety_verdict.get("verdict") or "").upper()
        return verdict == "APPROVED"
    upper = str(safety_verdict).upper()
    return "APPROVED" in upper and "ABSTAIN" not in upper


def should_seed_cache(
    *,
    response: str = "",
    abstained: bool = False,
    safety_verdict: Any = None,
    require_safety: bool = False,
    grounding_score: Optional[float] = None,
    groundedness_floor: float = 0.0,
) -> tuple[bool, str]:
    """
    Return (allowed, reason). Seed only when all quality bars hold.
    """
    if abstained:
        return False, "abstained"
    if is_refusal_response(response):
        return False, "refusal_response"
    if require_safety and not safety_approving(safety_verdict):
        return False, "safety_not_approved"
    if grounding_score is not None and grounding_score < groundedness_floor:
        return False, "grounding_below_floor"
    return True, "ok"


__all__ = ["is_refusal_response", "safety_approving", "should_seed_cache"]
