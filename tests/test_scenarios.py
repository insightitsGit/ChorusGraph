"""Scenario naming and registry tests (no Gemini)."""

from __future__ import annotations

from benchmark.scenarios import SCENARIO_MATRIX, make_runner


def test_scenario_matrix_covers_eight_pairs():
    assert len(SCENARIO_MATRIX) == 4
    assert SCENARIO_MATRIX[("finance", "single")] == ("FL1", "FC1")
    assert SCENARIO_MATRIX[("healthcare", "multi")] == ("HL2", "HC2")


def test_make_runner_returns_expected_types():
    assert make_runner("FL1").__class__.__name__ == "FL1Runner"
    assert make_runner("FC2").__class__.__name__ == "FC2Runner"
    assert make_runner("HL1").__class__.__name__ == "HL1Runner"
    assert make_runner("HC2").__class__.__name__ == "HC2Runner"
