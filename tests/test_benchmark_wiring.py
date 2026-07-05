"""Benchmark harness wiring preflight."""

from __future__ import annotations

from benchmark.wiring import verify_benchmark_wiring


def test_benchmark_wiring_preflight():
    lines = verify_benchmark_wiring()
    assert any("HC1" in ln for ln in lines)
    assert any("depth-6" in ln for ln in lines)
