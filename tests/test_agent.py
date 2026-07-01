"""Unified Agent type tests — knobs + belief stubs."""

from __future__ import annotations

import json

import pytest

from chorusgraph.agents.agent import Agent
from chorusgraph.agents.policy import (
    BeliefPolicy,
    BeliefPolicyNotCalibratedError,
    PlanPolicy,
    PlanSolveOpts,
    ReActOpts,
    ReflectionOpts,
)
from chorusgraph.agents.reflection import ValidationVerdict, run_reflection
from chorusgraph.nodes.tool import default_finance_registry


def _stub_react_llm(responses: list[dict]):
    call = {"n": 0}

    def llm_json(_s: str, _u: str) -> str:
        idx = min(call["n"], len(responses) - 1)
        call["n"] += 1
        return json.dumps(responses[idx])

    return llm_json, call


def test_belief_policy_raises_when_enabled():
    agent = Agent(
        pattern="react",
        tools=default_finance_registry(),
        model=lambda _s, _u: "{}",
        belief=BeliefPolicy(confidence_stop=0.9),
    )
    with pytest.raises(BeliefPolicyNotCalibratedError):
        agent.run("test")


def test_stop_on_repeated_action_breaks_loop():
    registry = default_finance_registry()
    action = {
        "tool": "fetch_exchange_rate",
        "args": {"from_currency": "USD", "to_currency": "EUR"},
    }
    llm, _ = _stub_react_llm(
        [
            {"thought": "fetch", "action": action, "finish": False},
            {"thought": "repeat", "action": action, "finish": False},
            {"thought": "done", "action": None, "finish": True},
        ]
    )
    agent = Agent(
        pattern="react",
        tools=registry,
        model=llm,
        policy=PlanPolicy(max_steps=8),
        pattern_opts=ReActOpts(stop_on_repeated_action=True, max_tool_calls=8),
    )
    result = agent.run("USD EUR rate")
    assert result.finish_reason == "repeated_action"
    assert len(result.tool_calls) == 1


def test_require_tool_before_finish_blocks_early_finish():
    registry = default_finance_registry()
    llm, calls = _stub_react_llm(
        [
            {"thought": "finish early", "action": None, "finish": True},
            {
                "thought": "must fetch",
                "action": {"tool": "fetch_exchange_rate", "args": {"from_currency": "USD", "to_currency": "EUR"}},
                "finish": False,
            },
            {"thought": "done", "action": None, "finish": True},
        ]
    )
    agent = Agent(
        pattern="react",
        tools=registry,
        model=llm,
        policy=PlanPolicy(max_steps=6),
        pattern_opts=ReActOpts(require_tool_before_finish=True, max_tool_calls=4),
    )
    result = agent.run("USD EUR rate")
    assert len(result.tool_calls) >= 1
    assert calls["n"] >= 2


def test_max_revisions_caps_reflection():
    def validate(text: str) -> ValidationVerdict:
        return ValidationVerdict(approved=False, notes=["nope"])

    def revise(text: str, _v: ValidationVerdict) -> str:
        return text + " fix"

    result = run_reflection(
        initial_draft="draft",
        validate=validate,
        revise=revise,
        pattern_opts=ReflectionOpts(max_revisions=2),
    )
    assert result.passes == 2
    assert result.approved is False


def test_plan_solve_skip_on_step_failure():
    registry = default_finance_registry()
    plan = json.dumps(
        {
            "steps": [
                {
                    "id": 1,
                    "description": "bad calc",
                    "tool": "compound_interest",
                    "args": {"principal": -1, "annual_rate_pct": 5, "years": 1},
                },
                {
                    "id": 2,
                    "description": "Fetch USD/EUR",
                    "tool": "fetch_exchange_rate",
                    "args": {"from_currency": "USD", "to_currency": "EUR"},
                },
            ]
        }
    )
    agent = Agent(
        pattern="plan_solve",
        tools=registry,
        model=lambda _s, _u: plan,
        pattern_opts=PlanSolveOpts(on_step_failure="skip", max_plan_steps=5),
    )
    result = agent.run("FX plan")
    assert result.failed_step is None
    assert len(result.tool_calls) == 2
    assert result.tool_calls[-1]["ok"] is True


def test_agent_run_react_matches_run_react_shim():
    from chorusgraph.agents.react import run_react

    registry = default_finance_registry()
    llm, _ = _stub_react_llm(
        [
            {
                "thought": "fetch",
                "action": {"tool": "fetch_exchange_rate", "args": {"from_currency": "USD", "to_currency": "EUR"}},
                "finish": False,
            },
            {"thought": "done", "action": None, "finish": True},
        ]
    )
    policy = PlanPolicy(max_steps=4)
    opts = ReActOpts(max_tool_calls=4)
    via_agent = Agent(pattern="react", tools=registry, model=llm, policy=policy, pattern_opts=opts).run("USD EUR")
    llm2, _ = _stub_react_llm(
        [
            {
                "thought": "fetch",
                "action": {"tool": "fetch_exchange_rate", "args": {"from_currency": "USD", "to_currency": "EUR"}},
                "finish": False,
            },
            {"thought": "done", "action": None, "finish": True},
        ]
    )
    via_shim = run_react(question="USD EUR", registry=registry, llm_json=llm2, policy=policy, pattern_opts=opts)
    assert len(via_agent.tool_calls) == len(via_shim.tool_calls) == 1
    assert via_agent.tool_calls[0]["ok"] is True
