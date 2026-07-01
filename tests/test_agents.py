"""Unit tests for agent-loop substrate and prebuilts (real tools, stub LLM where noted)."""

from __future__ import annotations

import json

from chorusgraph.agents.loop import TraceKind, run_agent_loop
from chorusgraph.agents.plan_solve import run_plan_solve
from chorusgraph.agents.policy import PlanPolicy
from chorusgraph.agents.react import run_react
from chorusgraph.agents.reflection import ValidationVerdict, run_reflection
from chorusgraph.nodes.tool import default_finance_registry


def test_agent_loop_records_trace():
    def reason(*, scratchpad: str, step: int):
        if step == 0:
            return {"thought": "need data", "action": {"tool": "ping"}, "finish": False}
        return {"thought": "done", "finish": True, "finish_reason": "complete"}

    def act(action):
        return {"ok": True}

    def route(*, reason_result, observations):
        if reason_result.get("finish"):
            return "finish"
        return "act"

    outcome = run_agent_loop(
        policy=PlanPolicy(max_steps=4),
        reason=reason,
        act=act,
        route=route,
    )
    kinds = [s.kind for s in outcome.trace]
    assert TraceKind.THOUGHT in kinds
    assert TraceKind.ACTION in kinds
    assert TraceKind.OBSERVATION in kinds


def test_react_two_tool_calls_real_frankfurter():
    registry = default_finance_registry()
    call_n = {"n": 0}

    def llm_json(system: str, user: str) -> str:
        call_n["n"] += 1
        if call_n["n"] == 1:
            return json.dumps(
                {
                    "thought": "Fetch USD/EUR first",
                    "action": {
                        "tool": "fetch_exchange_rate",
                        "args": {"from_currency": "USD", "to_currency": "EUR"},
                    },
                    "finish": False,
                }
            )
        if call_n["n"] == 2:
            return json.dumps(
                {
                    "thought": "Fetch USD/GBP next",
                    "action": {
                        "tool": "fetch_exchange_rate",
                        "args": {"from_currency": "USD", "to_currency": "GBP"},
                    },
                    "finish": False,
                }
            )
        return json.dumps({"thought": "Have both rates", "action": None, "finish": True})

    result = run_react(
        question="Compare USD/EUR and USD/GBP",
        registry=registry,
        llm_json=llm_json,
        policy=PlanPolicy(max_steps=5),
    )
    assert len(result.tool_calls) == 2
    assert all(tc["ok"] for tc in result.tool_calls)
    assert any(s.kind.value == "thought" for s in result.trace)


def test_reflection_fixes_wrong_figure():
    def validate(text: str) -> ValidationVerdict:
        if "0.9900" in text:
            return ValidationVerdict(approved=False, notes=["wrong rate"])
        if "0.878" in text or "0.87" in text:
            return ValidationVerdict(approved=True, notes=[])
        return ValidationVerdict(approved=False, notes=["missing rate"])

    def revise(text: str, verdict: ValidationVerdict) -> str:
        return "The USD/EUR rate is 0.8785 per tool data."

    result = run_reflection(
        initial_draft="The USD/EUR rate is 0.9900 (incorrect).",
        validate=validate,
        revise=revise,
        policy=PlanPolicy(max_reflection_passes=2),
    )
    assert result.approved is True
    assert "0.8785" in result.draft
    assert any(s.kind.value == "revision" for s in result.trace)


def test_plan_solve_static_execution():
    registry = default_finance_registry()
    plan_json = json.dumps(
        {
            "steps": [
                {
                    "id": 1,
                    "description": "Fetch USD/EUR",
                    "tool": "fetch_exchange_rate",
                    "args": {"from_currency": "USD", "to_currency": "EUR"},
                },
                {
                    "id": 2,
                    "description": "Fetch USD/GBP",
                    "tool": "fetch_exchange_rate",
                    "args": {"from_currency": "USD", "to_currency": "GBP"},
                },
            ]
        }
    )

    result = run_plan_solve(
        question="Multi-step FX",
        registry=registry,
        llm_json=lambda _s, _u: plan_json,
        policy=PlanPolicy(max_steps=5),
    )
    assert len(result.plan) == 2
    assert len(result.tool_calls) == 2
    assert any(s.kind.value == "plan_step" for s in result.trace)
