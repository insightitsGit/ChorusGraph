"""Shared deterministic abstain gate for healthcare C and D pipelines."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def safety_verdict_from_text(text: str) -> Dict[str, Any]:
    """Map free-text safety output (container C) to structured verdict."""
    upper = (text or "").upper()
    if "ABSTAIN" in upper:
        return {"verdict": "ABSTAIN", "missing_evidence": [], "reason": (text or "")[:150]}
    return {"verdict": "APPROVED", "missing_evidence": [], "reason": (text or "")[:150]}


def retrieve_artifact_from_docs(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    cited = [str(d.get("id") or "") for d in docs if d.get("id")]
    return {"cited_ids": cited}


def should_abstain(
    *,
    case_topic: str,
    retrieve_artifact: Optional[Dict[str, Any]],
    retrieved_docs: List[Dict[str, Any]],
    safety_verdict: Dict[str, Any],
) -> bool:
    """Deterministic abstain gate — evidence first, then safety verdict."""
    cited = [c for c in ((retrieve_artifact or {}).get("cited_ids") or []) if c]
    verdict = str(safety_verdict.get("verdict") or "").upper()

    if case_topic == "safety" and not cited:
        return True
    if not retrieved_docs and not cited:
        return True
    if verdict == "APPROVED":
        return False
    if verdict == "ABSTAIN":
        return True
    missing = [m for m in (safety_verdict.get("missing_evidence") or []) if m]
    return bool(missing)
