"""Measured fan-out benchmark scenario."""

from __future__ import annotations

from benchmark.scenarios_fanout import run_offline_fanout_benchmark


def test_offline_fanout_metrics_recorded():
    metrics = run_offline_fanout_benchmark()
    assert metrics["branches_requested"] == 3
    assert metrics["branches_executed"] == 2
    assert metrics["wall_ms"] >= 0
    assert metrics["llm_calls"] == 1
