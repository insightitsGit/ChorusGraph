"""Ledger helpers for cache gate and memory instrumentation."""

from __future__ import annotations

from typing import Any, Dict, Optional

from chorusgraph.cache_gate.decision import Decision
from chorusgraph.ledger.models import LedgerStep, RouteLedger


def annotate_cache_step(
    ledger: RouteLedger,
    step_index: int,
    decision: Decision,
) -> None:
    """Populate cache_hit and cache_score on an existing ledger step."""
    if step_index < 0 or step_index >= len(ledger.steps):
        return
    step = ledger.steps[step_index]
    detail = dict(step.detail or {})
    detail["decision_kind"] = decision.kind.value
    if decision.created_at is not None:
        detail["created_at"] = decision.created_at
    if getattr(decision, "force_refresh", False):
        detail["force_refresh"] = True
    ledger.steps[step_index] = step.model_copy(
        update={
            "cache_hit": decision.is_hit,
            "cache_score": decision.coarse_score if decision.is_hit else decision.verify_score or decision.coarse_score,
            "kind": step.kind or "cache.decision",
            "detail": detail,
        }
    )


def make_cache_gate_step(
    node: str,
    decision: Decision,
    *,
    duration_ms: int = 0,
) -> LedgerStep:
    """Create a ledger step for a cache_gate evaluation."""
    detail: Dict[str, Any] = {"decision_kind": decision.kind.value}
    if decision.created_at is not None:
        detail["created_at"] = decision.created_at
    if getattr(decision, "force_refresh", False):
        detail["force_refresh"] = True
    return LedgerStep(
        node=node,
        duration_ms=duration_ms,
        cache_hit=decision.is_hit,
        cache_score=(
            decision.verify_score
            if decision.is_hit
            else (decision.verify_score or decision.coarse_score)
        ),
        kind="cache.decision",
        detail=detail,
    )


def make_custom_step(
    node: str,
    *,
    kind: str,
    detail: Optional[Dict[str, Any]] = None,
    duration_ms: int = 0,
    rule_chain: Optional[list] = None,
) -> LedgerStep:
    """Third-party ledger step (e.g. kind='shine.verdict')."""
    return LedgerStep(
        node=node,
        duration_ms=duration_ms,
        kind=kind,
        detail=detail,
        rule_chain=list(rule_chain or []),
    )


def make_memory_step(
    node: str,
    *,
    confidence: float,
    duration_ms: int = 0,
) -> LedgerStep:
    """Ledger step with Cortex recall confidence as grounding_score."""
    return LedgerStep(
        node=node,
        duration_ms=duration_ms,
        grounding_score=confidence,
        rule_chain=[f"memory_confidence={confidence:.3f}"],
    )
