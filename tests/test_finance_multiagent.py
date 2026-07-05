"""Offline tests for finance multi-agent E vs F."""

from __future__ import annotations

from unittest.mock import patch

from benchmark.fl2.runner import FL2Runner, build_finance_graph_fl2
from benchmark.fc2.nodes import build_finance_graph_fc2, route_after_cache_fc2
from benchmark.fc2.runner import FC2Runner
from benchmark.fc2.trace import clear_trace, trace_path
from benchmark.finance_multiagent_shared import heuristic_tool_plan
from benchmark.multiagent_measure import hop_names
from benchmark.workload import WorkloadTask, generate_workload


class _StubFinanceGemini:
    def __init__(self) -> None:
        from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient, LlmUsage

        self.usage = LlmUsage()
        self._client = None
        self.model = "stub"

    def reset_usage(self) -> None:
        self.usage.reset()

    def generate(self, system: str, user: str, history=None) -> str:
        self.usage.record(prompt_tokens=40, output_tokens=20)
        if "planning" in system.lower() or "plan" in system.lower():
            if "compound" in user.lower() or "10,000" in user:
                return (
                    '{"plan":"compound","tools":[{"tool":"compound_interest",'
                    '"args":{"principal":10000,"annual_rate":0.05,"years":3,"compounds_per_year":12}}]}'
                )
            return (
                '{"plan":"fx","tools":[{"tool":"fetch_exchange_rate",'
                '"args":{"from_currency":"USD","to_currency":"EUR"}}]}'
            )
        if "writer" in system.lower():
            return "The USD/EUR exchange rate is 0.87727 based on live tool data."
        if "validator" in system.lower():
            return "The USD/EUR exchange rate is 0.87727 based on live tool data."
        return "ok"


def test_heuristic_tool_plan_fx():
    plan, msg = heuristic_tool_plan("What is the USD to EUR exchange rate today?")
    assert plan
    assert plan[0]["tool"] == "fetch_exchange_rate"


def test_heuristic_compare_plan():
    plan, _ = heuristic_tool_plan("Compare USD to EUR and USD to GBP exchange rates")
    assert len(plan) == 2


def test_container_e_graph_runs_fx_task():
    task = WorkloadTask(
        task_id="e-test-001",
        session_id="session-000",
        message="What is the USD to EUR exchange rate today?",
        category_slug="fx_rates",
        variant="novel",
        canonical_id="usd_eur",
    )
    stub = _StubFinanceGemini()
    graph, _ = build_finance_graph_fl2(gemini=stub)
    result = graph.invoke(
        {
            "task": task,
            "message": task.message,
            "conversation_history": [],
            "context": "",
            "tool_calls": [],
            "tool_results": [],
            "hop_metrics": [],
        }
    )
    hops = hop_names(result.get("hop_metrics") or [])
    assert hops == ["researcher", "tool", "writer", "validator"]
    assert int(len(result.get("tool_calls") or [])) >= 1
    assert result.get("response")


def test_container_e_runner_offline():
    task = WorkloadTask(
        task_id="e-test-002",
        session_id="session-001",
        message="What is the USD to EUR exchange rate today?",
        category_slug="fx_rates",
        variant="novel",
        canonical_id="usd_eur",
    )
    runner = FL2Runner()
    with patch.object(runner, "_gemini", _StubFinanceGemini()):
        m = runner.run(task)
    assert m.container == "FL2"
    assert m.hop_metrics
    assert len(m.hop_metrics) == 4


def test_workload_generates_tasks_for_multiagent():
    tasks = generate_workload(12, seed=42, repeat_band_pct=40)
    assert len(tasks) == 12
    assert any(t.variant == "exact_repeat" for t in tasks)


def test_route_after_cache_fc2_skips_to_writer():
    assert route_after_cache_fc2({"cache_hit": True, "tool_result": {"rate": 0.9}}) == "writer"
    assert route_after_cache_fc2({"cache_hit": False}) == "researcher"


def test_container_f_graph_cache_hit_path_offline():
    clear_trace()
    task = WorkloadTask(
        task_id="f-test-cache",
        session_id="session-f-001",
        message="What is the USD to EUR exchange rate today?",
        category_slug="fx_rates",
        variant="exact_repeat",
        canonical_id="usd_eur",
    )
    stub = _StubFinanceGemini()
    graph, _, runtime = build_finance_graph_fc2(gemini=stub)
    runtime.seed_tool_cache(task.message, {"from_currency": "USD", "to_currency": "EUR", "rate": 0.87727})

    result = graph.invoke(
        {
            "task": task,
            "message": task.message,
            "conversation_history": [],
            "tool_calls": [],
            "tool_results": [],
            "hop_metrics": [],
            "vector_hops": [],
            "prism_sequence": [],
            "cache_seed_phrases": [],
        }
    )
    hops = hop_names(result.get("hop_metrics") or [])
    assert "researcher" not in hops
    assert "tool" not in hops
    assert hops == ["vector_ingress", "cache_gate", "writer", "validator"]
    assert result.get("cache_hit") is True
    assert trace_path().exists()
