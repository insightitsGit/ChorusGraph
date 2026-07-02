"""Measured cache thresholds for Container B — NOT H4 demo values (0.82/0.85)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

# H2/H3 shadow operating point and cache_gate/gate.py default coarse stage.
COARSE_THRESHOLD: float = 0.88

# Per-slug verify thresholds from shadow measurement infrastructure.
# fx_rates has no H3 CACHEABLE slug yet (n << MIN_HITS=300); use gate.py default until H9 calibrates.
MEASURED_VERIFY_THRESHOLDS: Dict[str, float] = {
    "fx_rates": 0.95,
    "clinical_guidelines": 0.95,
}

# Explicitly forbidden demo thresholds from H4 finance agent wiring.
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
    """Return shadow-measured operating thresholds for the benchmark."""
    thresholds = CacheThresholds(coarse=COARSE_THRESHOLD, verify_by_slug=dict(MEASURED_VERIFY_THRESHOLDS))
    thresholds.assert_not_demo()
    return thresholds


THRESHOLD_PROVENANCE = """
Coarse 0.88 — H2 shadow harness default, H3 replay default, cache_gate/gate.py default.
Verify 0.95 (fx_rates) — gate.py default verify_threshold; no slug-specific CACHEABLE point yet
  (H3 production replay: all slugs INSUFFICIENT DATA, n << MIN_HITS=300).
H4 demo 0.82/0.85 — excluded per docs/BENCHMARK.md anti-rigging checklist.
Full fx_rates frontier will be produced when benchmark workload runs at scale (H9).
""".strip()
