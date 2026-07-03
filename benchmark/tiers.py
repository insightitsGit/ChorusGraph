"""Benchmark workload tiers — light / mid / heavy task counts."""

from __future__ import annotations

from typing import Literal

TierName = Literal["light", "mid", "heavy"]

# Paired tasks per scenario (same finance workload + healthcare cases).
TIER_TASKS: dict[TierName, int] = {
    "light": 40,   # smoke / CI / quick Azure (~320 scenario-runs for all 8)
    "mid": 100,    # regression
    "heavy": 300,  # scale / shadow threshold calibration
}

TIER_REPEAT_BAND: dict[TierName, int] = {
    "light": 40,
    "mid": 40,
    "heavy": 40,
}


def tasks_for_tier(tier: TierName) -> int:
    return TIER_TASKS[tier]


def repeat_band_for_tier(tier: TierName) -> int:
    return TIER_REPEAT_BAND[tier]


__all__ = ["TIER_REPEAT_BAND", "TIER_TASKS", "TierName", "repeat_band_for_tier", "tasks_for_tier"]
