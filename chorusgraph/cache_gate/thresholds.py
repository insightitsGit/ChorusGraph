"""Shadow-measured cache thresholds — product source of truth."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

COARSE_THRESHOLD: float = 0.88

MEASURED_VERIFY_THRESHOLDS: Dict[str, float] = {
    "fx_rates": 0.95,
    "compound_savings": 0.95,
    "clinical_guidelines": 0.95,
}

H4_DEMO_COARSE = 0.82
H4_DEMO_VERIFY = 0.85


@dataclass(frozen=True)
class CacheThresholds:
    coarse: float
    verify_by_slug: Dict[str, float]

    def verify_for(self, slug: str) -> float:
        return self.verify_by_slug.get(slug, 0.95)

    def assert_not_demo(self) -> None:
        if self.coarse == H4_DEMO_COARSE or any(v == H4_DEMO_VERIFY for v in self.verify_by_slug.values()):
            raise ValueError(
                "Benchmark must not use H4 demo thresholds (0.82/0.85). "
                "Use measured shadow operating point instead."
            )


def measured_thresholds() -> CacheThresholds:
    thresholds = CacheThresholds(coarse=COARSE_THRESHOLD, verify_by_slug=dict(MEASURED_VERIFY_THRESHOLDS))
    thresholds.assert_not_demo()
    return thresholds


__all__ = [
    "COARSE_THRESHOLD",
    "CacheThresholds",
    "H4_DEMO_COARSE",
    "H4_DEMO_VERIFY",
    "MEASURED_VERIFY_THRESHOLDS",
    "measured_thresholds",
]
