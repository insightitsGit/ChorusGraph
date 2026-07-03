"""Per-hop measurement for multi-agent C vs D benchmark."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional

ContainerId = Literal["HL1", "HC1", "HL2", "HC2"]


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
    cache_hit: Optional[bool] = None
    cache_score: Optional[float] = None
    variant: str = "novel"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["hop_metrics"] = [asdict(h) for h in self.hop_metrics]
        return d


def hop_names(hop_metrics: List[Any]) -> List[str]:
    names: List[str] = []
    for h in hop_metrics:
        if isinstance(h, dict):
            names.append(str(h.get("hop") or ""))
        else:
            names.append(str(getattr(h, "hop", "") or ""))
    return names


def totals_from_hops(hop_metrics: List[Any]) -> tuple[int, int, int]:
    """Sum llm_calls, tokens_in, tokens_out across all hops."""
    def _val(h: Any, key: str) -> int:
        if isinstance(h, dict):
            return int(h.get(key) or 0)
        return int(getattr(h, key, 0) or 0)

    return (
        sum(_val(h, "llm_calls") for h in hop_metrics),
        sum(_val(h, "tokens_in") for h in hop_metrics),
        sum(_val(h, "tokens_out") for h in hop_metrics),
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
