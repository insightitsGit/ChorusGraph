"""Measured cache thresholds for FC1 — re-export from product source of truth."""

from __future__ import annotations

from chorusgraph.cache_gate.thresholds import (
    COARSE_THRESHOLD,
    H4_DEMO_COARSE,
    H4_DEMO_VERIFY,
    MEASURED_VERIFY_THRESHOLDS,
    CacheThresholds,
    measured_thresholds,
)


THRESHOLD_PROVENANCE = """
Coarse 0.88 — H2 shadow harness default, H3 replay default, cache_gate/gate.py default.
Verify 0.95 (fx_rates) — gate.py default verify_threshold; no slug-specific CACHEABLE point yet
  (H3 production replay: all slugs INSUFFICIENT DATA, n << MIN_HITS=300).
H4 demo 0.82/0.85 — excluded per docs/BENCHMARK.md anti-rigging checklist.
Full fx_rates frontier will be produced when benchmark workload runs at scale (H9).
""".strip()
