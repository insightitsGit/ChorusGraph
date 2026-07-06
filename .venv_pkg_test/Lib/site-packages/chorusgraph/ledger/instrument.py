"""Ledger helpers for cache gate and memory instrumentation."""

from __future__ import annotations

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
    ledger.steps[step_index] = step.model_copy(
        update={
            "cache_hit": decision.is_hit,
            "cache_score": decision.coarse_score if decision.is_hit else decision.verify_score or decision.coarse_score,
        }
    )


def make_cache_gate_step(
    node: str,
    decision: Decision,
    *,
    duration_ms: int = 0,
) -> LedgerStep:
    """Create a ledger step for a cache_gate evaluation."""
    return LedgerStep(
        node=node,
        duration_ms=duration_ms,
        cache_hit=decision.is_hit,
        cache_score=(
            decision.verify_score
            if decision.is_hit
            else (decision.verify_score or decision.coarse_score)
        ),
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
