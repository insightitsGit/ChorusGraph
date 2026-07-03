"""Measured fan-out benchmark scenario."""

from __future__ import annotations

from benchmark.scenarios_fanout import (
    HEALTHCARE_DRUG_PAIRS,
    HOPS_PER_BRANCH,
    run_offline_fanout_benchmark,
)


def test_offline_fanout_metrics_recorded():
    metrics = run_offline_fanout_benchmark()
    assert metrics["branches_requested"] >= 20
    assert metrics["branches_executed"] == metrics["branches_requested"]
    assert metrics["healthcare_depth"] == 6
    assert metrics["wall_ms"] >= 0
    assert metrics["parallel_wall_ms"] == metrics["wall_ms"]
    assert metrics["serial_wall_ms"] >= 0
    assert metrics["llm_calls"] == metrics["branches_executed"] * HOPS_PER_BRANCH
    assert metrics["serial_llm_calls"] == metrics["branches_executed"] * HOPS_PER_BRANCH
    assert metrics["speedup_vs_serial"] is not None
    assert len(HEALTHCARE_DRUG_PAIRS) >= 20
