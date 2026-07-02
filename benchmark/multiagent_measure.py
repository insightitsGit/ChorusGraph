"""Per-hop measurement for multi-agent C vs D benchmark."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional

ContainerId = Literal["C", "D"]


@dataclass
class HopMetric:
    hop: str
    latency_ms: int
    llm_calls: int
    tokens_in: int
    tokens_out: int
    tool_calls: int = 0


@dataclass
class MultiAgentMeasurement:
    case_id: str
    container: ContainerId
    pipeline_depth: int
    message: str
    latency_ms: int
    llm_calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    task_success: bool
    abstained: bool
    answer: str
    tool_calls: int = 0
    hop_metrics: List[HopMetric] = field(default_factory=list)
    embed_count: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["hop_metrics"] = [asdict(h) for h in self.hop_metrics]
        return d


def totals_from_hops(hop_metrics: List[HopMetric]) -> tuple[int, int, int]:
    """Sum llm_calls, tokens_in, tokens_out across all hops."""
    return (
        sum(h.llm_calls for h in hop_metrics),
        sum(h.tokens_in for h in hop_metrics),
        sum(h.tokens_out for h in hop_metrics),
    )


def score_healthcare_answer(
    *,
    answer: str,
    must_cite: List[str],
    expected_abstain: bool,
    abstained: bool,
) -> bool:
    text = (answer or "").lower()
    if expected_abstain:
        return abstained or "abstain" in text or "cannot" in text or "insufficient" in text
    if abstained:
        return False
    return all(term.lower() in text for term in must_cite)
