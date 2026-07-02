"""Belief-tier threshold calibration from benchmark distributions (§7.5)."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional

from benchmark.measure import TaskMeasurement


@dataclass(frozen=True)
class BeliefCalibration:
    confidence_stop: Optional[float]
    groundedness_floor: Optional[float]
    memory_confidence_gate: Optional[float]
    sample_cache_scores: int
    sample_grounding_scores: int
    notes: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "confidence_stop": self.confidence_stop,
            "groundedness_floor": self.groundedness_floor,
            "memory_confidence_gate": self.memory_confidence_gate,
            "sample_cache_scores": self.sample_cache_scores,
            "sample_grounding_scores": self.sample_grounding_scores,
            "notes": self.notes,
        }


def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    values = sorted(values)
    idx = max(0, min(len(values) - 1, int(len(values) * p)))
    return round(values[idx], 4)


def calibrate_from_measurements(b_rows: List[TaskMeasurement]) -> BeliefCalibration:
    """
    Derive LATER BeliefPolicy thresholds from measured B distributions.

    - confidence_stop: 5th percentile of cache_score on successful cache hits
      (conservative stop when confidence drops below historical hit quality).
    - groundedness_floor: 10th percentile of grounding_score when memory recall fired.
    - memory_confidence_gate: same as groundedness_floor (Cortex confidence proxy).
    """
    notes: List[str] = []
    hit_scores = [
        float(r.cache_score)
        for r in b_rows
        if r.cache_hit and r.cache_score is not None and r.task_success
    ]
    miss_scores = [
        float(r.cache_score)
        for r in b_rows
        if not r.cache_hit and r.cache_score is not None
    ]
    grounding = [float(r.grounding_score) for r in b_rows if r.grounding_score is not None]

    confidence_stop = _percentile(hit_scores, 0.05)
    if confidence_stop is None and miss_scores:
        confidence_stop = _percentile(miss_scores, 0.50)
        notes.append("confidence_stop from median cache_score on misses (no successful hits yet)")

    groundedness_floor = _percentile(grounding, 0.10)
    if groundedness_floor is None:
        notes.append("groundedness_floor unavailable — no Cortex recall in benchmark tasks")

    if hit_scores and miss_scores:
        sep = statistics.mean(hit_scores) - statistics.mean(miss_scores)
        notes.append(f"cache_score separation (mean hit - miss): {sep:.4f}")

    return BeliefCalibration(
        confidence_stop=confidence_stop,
        groundedness_floor=groundedness_floor,
        memory_confidence_gate=groundedness_floor,
        sample_cache_scores=len(hit_scores) + len(miss_scores),
        sample_grounding_scores=len(grounding),
        notes=notes,
    )
