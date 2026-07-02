"""Benchmark rig unit tests — schema, workload, thresholds (no Gemini required)."""

from __future__ import annotations

import json
import os

import pytest

from benchmark.measure import ComparisonReport, TaskMeasurement
from benchmark.thresholds import H4_DEMO_COARSE, H4_DEMO_VERIFY, measured_thresholds
from benchmark.workload import REPEAT_BANDS, REPEAT_MODEL, generate_workload, repeat_model_for_band, workload_stats


def test_measured_thresholds_not_h4_demo():
    t = measured_thresholds()
    assert t.coarse != H4_DEMO_COARSE
    assert t.verify_for("fx_rates") != H4_DEMO_VERIFY
    assert t.coarse == 0.88


def test_repeat_bands_sum_to_one():
    for band, model in REPEAT_BANDS.items():
        total = sum(model.values())
        assert abs(total - 1.0) < 1e-9, f"band {band} weights sum to {total}"


def test_generate_workload_repeat_band_changes_distribution():
    low = generate_workload(200, seed=1, repeat_band_pct=20)
    high = generate_workload(200, seed=1, repeat_band_pct=60)
    low_stats = workload_stats(low)
    high_stats = workload_stats(high)
    assert low_stats["exact_repeat"] < high_stats["exact_repeat"]


def test_score_task_success_content_not_tool_calls():
    from benchmark.measure import score_task_success

    assert score_task_success(
        message="USD/EUR rate?",
        answer="The USD to EUR exchange rate is 0.8785 today.",
        canonical_id="usd_eur",
    )
    assert not score_task_success(
        message="USD/EUR rate?",
        answer="Sorry, no data.",
        canonical_id="usd_eur",
    )
    assert not score_task_success(
        message="What is the USD to JPY exchange rate today?",
        answer="EUR rate is 0.8785.",
        canonical_id="usd_jpy",
    )


def test_analyze_produces_ci():
    from benchmark.analyze import analyze_container, bootstrap_ci
    from benchmark.measure import TaskMeasurement

    rows = [
        TaskMeasurement(
            task_id=f"t{i}",
            session_id="s",
            container="A",
            message="q",
            variant="novel",
            latency_ms=100 + i,
            llm_calls=2,
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.001,
            task_success=True,
            answer="rate 0.88",
        )
        for i in range(20)
    ]
    metrics = analyze_container(rows)
    assert "latency_ms_p50" in metrics
    assert metrics["latency_ms_p50"].lower95 <= metrics["latency_ms_p50"].point <= metrics["latency_ms_p50"].upper95


def test_container_b_uses_react_path_constant():
    from benchmark.container_b.runner import B_REASONING_PATH

    assert "react" in B_REASONING_PATH.lower()


def test_belief_calibration_returns_dict():
    from benchmark.belief_calibration import calibrate_from_measurements
    from benchmark.measure import TaskMeasurement

    rows = [
        TaskMeasurement(
            task_id="t1",
            session_id="s",
            container="B",
            message="q",
            variant="exact_repeat",
            latency_ms=50,
            llm_calls=0,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            task_success=True,
            answer="0.8785",
            cache_hit=True,
            cache_score=0.95,
        )
    ]
    cal = calibrate_from_measurements(rows)
    assert cal.confidence_stop is not None


def test_workload_repeat_model_distribution():
    tasks = generate_workload(100, seed=7)
    stats = workload_stats(tasks)
    assert stats["total"] == 100
    assert stats["sessions"] >= 10
    model = repeat_model_for_band(40)
    for variant in model:
        assert stats[variant] >= 1


def test_workload_sessions_group_repeats():
    tasks = generate_workload(20, seed=42, tasks_per_session=5)
    by_session: dict[str, list] = {}
    for t in tasks:
        by_session.setdefault(t.session_id, []).append(t)
    assert len(by_session) == 4
    # Each session should have at least one repeat or paraphrase after seed
    for session_tasks in by_session.values():
        variants = {t.variant for t in session_tasks}
        assert "novel" in variants
        assert variants & {"exact_repeat", "paraphrase"}


def test_measurement_schema_shared_fields():
    row_a = TaskMeasurement(
        task_id="t1",
        session_id="s1",
        container="A",
        message="USD/EUR?",
        variant="novel",
        latency_ms=100,
        llm_calls=2,
        tokens_in=500,
        tokens_out=100,
        cost_usd=0.001,
        task_success=True,
        answer="rate is 0.88",
    )
    row_b = TaskMeasurement(
        task_id="t1",
        session_id="s1",
        container="B",
        message="USD/EUR?",
        variant="novel",
        latency_ms=80,
        llm_calls=1,
        tokens_in=400,
        tokens_out=90,
        cost_usd=0.0008,
        task_success=True,
        answer="rate is 0.88",
        cache_hit=False,
        cache_score=0.5,
        grounding_score=None,
    )
    keys_a = set(row_a.to_dict().keys())
    keys_b = set(row_b.to_dict().keys())
    shared = {
        "task_id",
        "session_id",
        "container",
        "message",
        "variant",
        "latency_ms",
        "llm_calls",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "task_success",
        "answer",
    }
    assert shared <= keys_a
    assert shared <= keys_b
    assert "cache_hit" in keys_b
    assert row_a.to_dict().get("cache_hit") is None


def test_comparison_report_skeleton():
    report = ComparisonReport(
        container_a=[
            TaskMeasurement(
                task_id="t1",
                session_id="s1",
                container="A",
                message="q",
                variant="novel",
                latency_ms=100,
                llm_calls=1,
                tokens_in=100,
                tokens_out=50,
                cost_usd=0.001,
                task_success=True,
                answer="ok",
            )
        ],
        container_b=[
            TaskMeasurement(
                task_id="t1",
                session_id="s1",
                container="B",
                message="q",
                variant="novel",
                latency_ms=50,
                llm_calls=0,
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
                task_success=True,
                answer="ok",
                cache_hit=True,
                cache_score=0.99,
            )
        ],
        workload_size=1,
    )
    summary = report.summary()
    assert summary["container_a"]["n"] == 1
    assert summary["container_b"]["n"] == 1
    assert "b_cache_hit_rate" in summary
    text = report.format_report()
    assert "no conclusions" in text.lower()


@pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"),
    reason="GEMINI_API_KEY required for live dry-run",
)
def test_dry_run_both_containers_two_tasks():
    from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key

    if not resolve_gemini_api_key():
        pytest.skip("GEMINI_API_KEY not available")

    from benchmark.run import run_benchmark

    report = run_benchmark(2, seed=99, containers=["A", "B"])
    assert len(report.container_a) == 2
    assert len(report.container_b) == 2
    for row in report.container_a + report.container_b:
        assert row.latency_ms >= 0
        assert row.llm_calls >= 0
        assert isinstance(row.answer, str)
    # Schema parity
    a_keys = set(report.container_a[0].to_dict().keys()) - {"cache_hit", "cache_score", "grounding_score"}
    b_keys = set(report.container_b[0].to_dict().keys())
    for key in a_keys:
        assert key in b_keys
