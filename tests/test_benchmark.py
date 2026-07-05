"""Benchmark rig unit tests — schema, workload, thresholds (no Gemini required)."""

from __future__ import annotations

import os

import pytest

from benchmark.measure import ComparisonReport, TaskMeasurement
from benchmark.thresholds import H4_DEMO_COARSE, H4_DEMO_VERIFY, measured_thresholds
from benchmark.workload import (
    REPEAT_BANDS,
    generate_workload,
    repeat_model_for_band,
    validate_workload_messages,
    workload_stats,
)


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
    low = generate_workload(200, seed=1, repeat_band_pct=20, include_memory_tasks=False)
    high = generate_workload(200, seed=1, repeat_band_pct=60, include_memory_tasks=False)
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
    from benchmark.analyze import analyze_container
    from benchmark.measure import TaskMeasurement

    rows = [
        TaskMeasurement(
            task_id=f"t{i}",
            session_id="s",
            container="FL1",
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
    assert (
        metrics["latency_ms_p50"].lower95
        <= metrics["latency_ms_p50"].point
        <= metrics["latency_ms_p50"].upper95
    )


def test_container_b_uses_react_path_constant():
    from benchmark.fc1.runner import FC1_REASONING_PATH

    assert "react" in FC1_REASONING_PATH.lower()


def test_belief_calibration_returns_dict():
    from benchmark.belief_calibration import calibrate_from_measurements
    from benchmark.measure import TaskMeasurement

    rows = [
        TaskMeasurement(
            task_id="t1",
            session_id="s",
            container="FC1",
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
    tasks = generate_workload(100, seed=7, include_memory_tasks=False)
    stats = workload_stats(tasks)
    assert stats["total"] == 100
    assert stats["sessions"] >= 10
    model = repeat_model_for_band(40)
    for variant in model:
        assert stats[variant] >= 1


def test_workload_message_matches_canonical_phrases():
    """Repeat/paraphrase messages must derive from their canonical_id phrase list."""
    tasks = generate_workload(500, seed=99, repeat_band_pct=40, include_memory_tasks=True)
    validate_workload_messages(tasks)
    repeats = [t for t in tasks if t.variant in ("exact_repeat", "paraphrase")]
    assert repeats, "need repeat variants to validate alignment"
    for task in repeats:
        assert task.canonical_id is not None
        from benchmark.workload import message_matches_canonical

        assert message_matches_canonical(task.message, task.canonical_id), (
            f"{task.task_id} {task.variant} canonical={task.canonical_id!r} message={task.message!r}"
        )


def test_workload_sessions_group_repeats():
    tasks = generate_workload(20, seed=42, tasks_per_session=5, include_memory_tasks=False)
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
        container="FL1",
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
        container="FC1",
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
                container="FL1",
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
                container="FC1",
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


def test_memory_workload_includes_seed_and_cross_recall():
    tasks = generate_workload(40, seed=11, tasks_per_session=5, memory_every_n_sessions=2)
    stats = workload_stats(tasks)
    assert stats["memory_seed"] >= 1
    assert stats["memory_recall_cross"] >= 1
    cross = [t for t in tasks if t.variant == "memory_recall_cross"]
    assert cross
    assert all(t.cross_session_recall for t in cross)
    assert all(t.memory_cortex_group for t in cross)
    seeds = [t for t in tasks if t.variant == "memory_seed"]
    assert seeds
    # Cross-session recall must land in a different session than its seed.
    for recall in cross:
        seed_sessions = {
            t.session_id for t in seeds if t.memory_cortex_group == recall.memory_cortex_group
        }
        assert recall.session_id not in seed_sessions


def test_pattern_state_declares_cache_score():
    from chorusgraph.examples.finance_agent.patterns_graph import PatternState

    assert "cache_score" in PatternState.__annotations__
    assert "cache_decision" in PatternState.__annotations__


def test_memory_rubric_scores_recall_terms():
    from benchmark.rubric import score_by_canonical

    assert score_by_canonical(
        canonical_id="memory_risk_conservative",
        message="What risk profile did I tell you?",
        answer="You described yourself as a conservative investor with low risk tolerance.",
        variant="memory_recall",
    )
    assert not score_by_canonical(
        canonical_id="memory_risk_conservative",
        message="What risk profile did I tell you?",
        answer="I do not have any information about your preferences.",
        variant="memory_recall",
    )


def test_belief_calibration_grounding_from_memory_rows():
    from benchmark.belief_calibration import calibrate_from_measurements

    rows = [
        TaskMeasurement(
            task_id="m1",
            session_id="s",
            container="FC1",
            message="recall",
            variant="memory_recall",
            latency_ms=100,
            llm_calls=2,
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.001,
            task_success=True,
            answer="conservative profile",
            grounding_score=0.82,
        ),
        TaskMeasurement(
            task_id="m2",
            session_id="s",
            container="FC1",
            message="recall",
            variant="memory_recall",
            latency_ms=100,
            llm_calls=2,
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.001,
            task_success=True,
            answer="long horizon",
            grounding_score=0.91,
        ),
    ]
    cal = calibrate_from_measurements(rows)
    assert cal.groundedness_floor is not None
    assert cal.sample_grounding_scores == 2


def test_slice_rows_fx_and_compound_excludes_memory():
    from benchmark.analyze import slice_rows

    rows = [
        TaskMeasurement(
            task_id="t1",
            session_id="s",
            container="FC1",
            message="q",
            variant="memory_recall_cross",
            latency_ms=1,
            llm_calls=1,
            tokens_in=1,
            tokens_out=1,
            cost_usd=0.0,
            task_success=True,
            answer="ok",
            category_slug="user_profile",
        ),
        TaskMeasurement(
            task_id="t2",
            session_id="s",
            container="FC1",
            message="fx",
            variant="novel",
            latency_ms=1,
            llm_calls=1,
            tokens_in=1,
            tokens_out=1,
            cost_usd=0.0,
            task_success=True,
            answer="ok",
            category_slug="fx_rates",
        ),
    ]
    fx = slice_rows(rows, "fx_and_compound")
    assert len(fx) == 1
    assert fx[0].task_id == "t2"


@pytest.mark.live
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
    a_keys = set(report.container_a[0].to_dict().keys()) - {
        "cache_hit",
        "cache_score",
        "grounding_score",
    }
    b_keys = set(report.container_b[0].to_dict().keys())
    for key in a_keys:
        assert key in b_keys
