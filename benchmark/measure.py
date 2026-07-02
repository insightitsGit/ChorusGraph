"""Identical per-task measurement schema for Container A and B."""

from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional

ContainerId = Literal["A", "B"]


def score_task_success(
    *,
    message: str,
    answer: str,
    error: Optional[str] = None,
    validation: Optional[Dict[str, Any]] = None,
) -> bool:
    """Fixed rubric applied identically to Container A and B."""
    import re

    if error:
        return False
    text = (answer or "").strip()
    if len(text) < 10:
        return False
    if validation and validation.get("approved") is False:
        return False
    lower_msg = message.lower()
    if any(w in lower_msg for w in ("rate", "usd", "eur", "gbp", "jpy", "exchange", "compound", "invest")):
        if not re.search(r"\d+\.\d+", text):
            return False
    return True


@dataclass
class TaskMeasurement:
    """Per-task row — shared schema across containers."""

    task_id: str
    session_id: str
    container: ContainerId
    message: str
    variant: str
    latency_ms: int
    llm_calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    task_success: bool
    answer: str
    # B-only (None for A)
    cache_hit: Optional[bool] = None
    cache_score: Optional[float] = None
    grounding_score: Optional[float] = None
    error: Optional[str] = None
    tool_calls: int = 0
    reasoning_path: Optional[str] = None
    repeat_band_pct: Optional[int] = None
    category_slug: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComparisonReport:
    """Aggregate skeleton — no conclusions, just comparable numbers."""

    container_a: List[TaskMeasurement] = field(default_factory=list)
    container_b: List[TaskMeasurement] = field(default_factory=list)
    workload_size: int = 0
    notes: List[str] = field(default_factory=list)

    def _aggregate(self, rows: List[TaskMeasurement]) -> Dict[str, Any]:
        if not rows:
            return {}
        latencies = [r.latency_ms for r in rows]
        return {
            "n": len(rows),
            "latency_ms_p50": int(statistics.median(latencies)),
            "latency_ms_p95": int(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)]),
            "total_cost_usd": round(sum(r.cost_usd for r in rows), 6),
            "cost_per_task_usd": round(sum(r.cost_usd for r in rows) / len(rows), 6),
            "task_success_rate": round(sum(1 for r in rows if r.task_success) / len(rows), 4),
            "total_llm_calls": sum(r.llm_calls for r in rows),
            "total_tokens_in": sum(r.tokens_in for r in rows),
            "total_tokens_out": sum(r.tokens_out for r in rows),
        }

    def summary(self) -> Dict[str, Any]:
        b_rows = self.container_b
        cache_hits = [r for r in b_rows if r.cache_hit]
        return {
            "workload_size": self.workload_size,
            "container_a": self._aggregate(self.container_a),
            "container_b": self._aggregate(b_rows),
            "b_cache_hit_rate": round(len(cache_hits) / len(b_rows), 4) if b_rows else 0.0,
            "notes": self.notes,
        }

    def format_report(self) -> str:
        lines = [
            "A/B Benchmark Comparison Report (skeleton — no conclusions)",
            "=" * 72,
            json.dumps(self.summary(), indent=2),
            "",
            "Sample rows (first 3 per container):",
        ]
        for label, rows in (("A", self.container_a), ("B", self.container_b)):
            lines.append(f"\n--- Container {label} ---")
            for row in rows[:3]:
                lines.append(json.dumps(row.to_dict(), indent=2))
        return "\n".join(lines)
