"""Cache gate decision types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class DecisionKind(str, Enum):
    MISS = "miss"
    HIT_REUSE = "hit_reuse"
    HIT_REVALIDATE = "hit_revalidate"
    HIT_AS_CONTEXT = "hit_as_context"


@dataclass(frozen=True)
class Decision:
    kind: DecisionKind
    value: Any = None
    coarse_score: float = 0.0
    verify_score: float = 0.0
    candidate_query: Optional[str] = None
    candidate_packet_id: Optional[str] = None

    @property
    def is_hit(self) -> bool:
        return self.kind != DecisionKind.MISS

    @property
    def counts_for_fp(self) -> bool:
        """Semantic hits never enter the FP numerator (ADR-002)."""
        return self.kind in (DecisionKind.HIT_REUSE, DecisionKind.HIT_REVALIDATE)
