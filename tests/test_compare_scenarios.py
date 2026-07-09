"""Group comparison tests — LangGraph vs ChorusGraph (no Gemini)."""

from __future__ import annotations

from benchmark.compare_scenarios import compare_all_groups, format_comparison_report
from benchmark.measure import TaskMeasurement


def _row(
    task_id: str,
    container: str,
    *,
    latency: int,
    success: bool,
    cost: float,
    llm: int,
    variant: str = "novel",
    cache_hit=None,
):
    return TaskMeasurement(
        task_id=task_id,
        session_id="s1",
        container=container,  # type: ignore[arg-type]
        message="test",
        variant=variant,
        latency_ms=latency,
        llm_calls=llm,
        tokens_in=100,
        tokens_out=50,
        cost_usd=cost,
        task_success=success,
        answer="ok",
        cache_hit=cache_hit,
    )


def test_finance_single_chorus_wins_on_latency_and_cost():
    results = {
        "FL1": [_row("t1", "FL1", latency=500, success=True, cost=0.002, llm=3) for _ in range(10)],
        "FC1": [
            _row("t1", "FC1", latency=200, success=True, cost=0.001, llm=1, cache_hit=True)
            for _ in range(10)
        ],
    }
    for i in range(10):
        results["FL1"][i] = _row(f"t{i}", "FL1", latency=500 + i, success=True, cost=0.002, llm=3)
        results["FC1"][i] = _row(
            f"t{i}", "FC1", latency=200 + i, success=True, cost=0.001, llm=1, cache_hit=i > 0
        )

    cmp = compare_all_groups(results)
    group = cmp["groups"]["finance_single"]
    assert group["scorecard"]["overall_winner"] == "chorusgraph"
    assert group["paired"]["n_paired"] == 10
    winners = {m["metric"]: m["winner"] for m in group["metrics"]}
    assert winners["latency_ms_p50"] == "chorusgraph"
    assert winners["cost_usd_per_task"] == "chorusgraph"


def test_comparison_report_renders_markdown():
    results = {
        "FL1": [_row("t1", "FL1", latency=100, success=True, cost=0.001, llm=2)],
        "FC1": [_row("t1", "FC1", latency=80, success=True, cost=0.0008, llm=1)],
    }
    md = format_comparison_report(compare_all_groups(results))
    assert "Finance Single" in md
    assert "LLM calls / task" in md
    assert "Task success" in md
    assert "Key metrics" in md


def test_comparison_report_honest_mode_banner():
    results = {
        "FL1": [_row("t1", "FL1", latency=100, success=True, cost=0.001, llm=2)],
        "FC1": [_row("t1", "FC1", latency=80, success=True, cost=0.0008, llm=1)],
    }
    md = format_comparison_report(compare_all_groups(results), cache_enabled=False)
    assert "Honest mode" in md
    assert "0% cache hits" in md


def test_finance_multi_error_rows_count_in_success_denominator():
    """Agent/tool errors must not be dropped from LangGraph rows only (FC2 fairness)."""
    tool_err = "Disallowed arguments for compound_interest: ['annual_rate']"
    results = {
        "FL2": [
            _row("t0", "FL2", latency=100, success=False, cost=0.001, llm=1),
            TaskMeasurement(
                task_id="t1",
                session_id="s1",
                container="FL2",
                message="compound",
                variant="novel",
                latency_ms=50,
                llm_calls=0,
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
                task_success=False,
                answer="",
                error=tool_err,
            ),
        ],
        "FC2": [
            _row("t0", "FC2", latency=90, success=True, cost=0.0009, llm=1),
            _row("t1", "FC2", latency=80, success=False, cost=0.0008, llm=1),
        ],
    }
    group = compare_all_groups(results)["groups"]["finance_multi"]
    assert group["n_langgraph"] == 2
    assert group["n_chorusgraph"] == 2
    success = next(m for m in group["metrics"] if m["metric"] == "task_success_rate")
    assert success["langgraph"]["point"] == 0.0
    assert success["chorusgraph"]["point"] == 0.5


def test_all_four_groups_when_data_present():
    base = [_row("x1", "FL1", latency=100, success=True, cost=0.001, llm=1)]
    results = {
        "FL1": base,
        "FC1": [_row("x1", "FC1", latency=90, success=True, cost=0.0009, llm=1)],
        "FL2": [_row("x1", "FL2", latency=100, success=True, cost=0.001, llm=1)],
        "FC2": [_row("x1", "FC2", latency=90, success=True, cost=0.0009, llm=1)],
        "HL1": [],
        "HC1": [],
        "HL2": [],
        "HC2": [],
    }
    cmp = compare_all_groups(results)
    assert set(cmp["groups"].keys()) == {"finance_single", "finance_multi"}


def test_abstain_rate_lower_is_better():
    """Lower abstain is better — ChorusGraph should win when it abstains less."""
    results = {
        "HL1": [
            {
                "case_id": f"t{i}",
                "container": "HL1",
                "variant": "novel",
                "latency_ms": 5000,
                "llm_calls": 3,
                "tokens_in": 100,
                "tokens_out": 50,
                "cost_usd": 0.001,
                "task_success": i % 2 == 0,
                "abstained": True,
            }
            for i in range(20)
        ],
        "HC1": [
            {
                "case_id": f"t{i}",
                "container": "HC1",
                "variant": "novel",
                "latency_ms": 4000,
                "llm_calls": 2,
                "tokens_in": 100,
                "tokens_out": 50,
                "cost_usd": 0.0008,
                "task_success": True,
                "abstained": i < 5,
            }
            for i in range(20)
        ],
    }
    group = compare_all_groups(results)["groups"]["healthcare_single"]
    abstain = next(m for m in group["metrics"] if m["metric"] == "abstain_rate")
    assert abstain["winner"] == "chorusgraph"
    assert abstain["chorusgraph"]["point"] < abstain["langgraph"]["point"]
