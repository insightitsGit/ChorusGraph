"""Finance execution pattern integration tests."""

from __future__ import annotations

import pytest

from chorusgraph import SqliteLedgerSink, wrap
from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key
from chorusgraph.examples.finance_agent.patterns_graph import (
    TENANT_ID,
    build_plan_solve_graph,
    build_react_graph,
    build_reflection_graph,
    pattern_initial_state,
)


@pytest.mark.live
@pytest.mark.skipif(not resolve_gemini_api_key(), reason="GEMINI_API_KEY not configured")
def test_react_pattern_two_tools_in_ledger():
    compiled, _ = build_react_graph()
    wrapped = wrap(
        compiled, tenant_id=TENANT_ID, graph_id="finance-react", sink=SqliteLedgerSink(":memory:")
    )
    result = wrapped.invoke(
        pattern_initial_state(
            "Compare USD to EUR and USD to GBP and tell me which is stronger against USD."
        )
    )
    assert len(result.get("tool_calls") or []) >= 2
    nodes = [s.node for s in wrapped.last_ledger.steps]
    assert any("/thought" in n for n in nodes)
    assert any("/action" in n for n in nodes)
    assert any("/observation" in n for n in nodes)


@pytest.mark.live
@pytest.mark.skipif(not resolve_gemini_api_key(), reason="GEMINI_API_KEY not configured")
def test_reflection_pattern_catches_wrong_figure():
    compiled, _ = build_reflection_graph()
    wrapped = wrap(
        compiled,
        tenant_id=TENANT_ID,
        graph_id="finance-reflection",
        sink=SqliteLedgerSink(":memory:"),
    )
    result = wrapped.invoke(
        pattern_initial_state(
            "What are USD/EUR and USD/GBP rates? Which is stronger against USD?",
            reflection_demo_wrong_figure=True,
            reflection_pass=0,
        )
    )
    nodes = [s.node for s in wrapped.last_ledger.steps]
    assert any("/revision" in n for n in nodes)
    validation = result.get("validation") or {}
    assert validation.get("approved") is True


@pytest.mark.live
@pytest.mark.skipif(not resolve_gemini_api_key(), reason="GEMINI_API_KEY not configured")
def test_plan_solve_pattern_end_to_end():
    compiled, _ = build_plan_solve_graph()
    wrapped = wrap(
        compiled, tenant_id=TENANT_ID, graph_id="finance-plan", sink=SqliteLedgerSink(":memory:")
    )
    result = wrapped.invoke(
        pattern_initial_state(
            "Fetch USD to EUR and USD to GBP rates, compute EUR/GBP cross-rate, and summarize."
        )
    )
    assert result.get("plan_steps")
    assert len(result.get("tool_calls") or []) >= 2
    nodes = [s.node for s in wrapped.last_ledger.steps]
    assert any("/plan_step" in n for n in nodes)
