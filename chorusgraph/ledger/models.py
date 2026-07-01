"""Route Ledger data models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LedgerStep(BaseModel):
    """One node transition recorded during a graph run."""

    node: str
    edge_taken: Optional[str] = None
    rule_chain: Optional[List[str]] = None
    duration_ms: int = 0
    timestamp: datetime = Field(default_factory=_utcnow)
    cache_hit: Optional[bool] = None
    cache_score: Optional[float] = None
    grounding_score: Optional[float] = None


class RouteLedger(BaseModel):
    """Durable per-run audit of graph execution."""

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    turn_id: Optional[str] = None
    tenant_id: str
    graph_id: str
    steps: List[LedgerStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)

    def add_step(self, step: LedgerStep) -> None:
        self.steps.append(step)
