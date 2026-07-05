"""Finance agent graph tests."""

from __future__ import annotations

import pytest

from chorusgraph import SqliteLedgerSink, wrap
from chorusgraph.cache_gate import gate
from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key
from chorusgraph.examples.finance_agent.graph import (
    GRAPH_ID,
    TENANT_ID,
    build_finance_graph,
    initial_state,
)
from chorusgraph.examples.finance_agent.nodes import (
    make_researcher_handler,
    make_tool_handler,
    seed_fx_cache_from_tool_calls,
)
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime
from chorusgraph.sections.models import CachePolicy, Section


def test_researcher_routes_fx_tool():
    runtime = FinanceRuntime(tenant_id="finance-test-routing")
    researcher = make_researcher_handler(runtime)
    out = researcher(
        {
            "message": "What is the USD to EUR exchange rate?",
            "cache_hit": False,
            "conversation_history": [],
        }
    )
    assert out["needs_tool"] is True
    assert out["tool_name"] == "fetch_exchange_rate"
    assert out["tool_args"]["from_currency"] == "USD"
    assert out["tool_args"]["to_currency"] == "EUR"


def test_researcher_uses_conversation_for_follow_up():
    runtime = FinanceRuntime(tenant_id="finance-test-followup")
    researcher = make_researcher_handler(runtime)
    history = [
        {"role": "user", "content": "What is the USD to EUR exchange rate today?"},
        {"role": "assistant", "content": "1 USD = 0.87 EUR"},
    ]
    out = researcher(
        {
            "message": "What about USD to GBP?",
            "cache_hit": False,
            "conversation_history": history,
        }
    )
    assert out["needs_tool"] is True
    assert out["tool_args"]["to_currency"] == "GBP"


def test_tool_node_executes_and_seeds_cache():
    runtime = FinanceRuntime(tenant_id="finance-test-tool")
    tool = make_tool_handler(runtime)
    state = {
        "needs_tool": True,
        "tool_name": "fetch_exchange_rate",
        "tool_args": {"from_currency": "USD", "to_currency": "EUR"},
        "message": "USD EUR rate please",
        "tool_calls": [],
    }
    out = tool(state)
    assert out["tool_result"]["rate"] > 0
    assert len(out["tool_calls"]) == 1
    assert out["tool_calls"][0]["ok"] is True

    section = Section(
        section_id="fx",
        category_slug="fx_rates",
        content=state["message"],
        cache_policy=CachePolicy.REPLAY_SAFE,
    )
    decision = gate(
        state["message"],
        section,
        runtime.cache,
        runtime.sidecar,
        coarse_threshold=0.82,
        verify_threshold=0.85,
    )
    assert decision.is_hit
    assert decision.value["rate"] == out["tool_result"]["rate"]


def test_react_path_seeds_fx_cache_from_tool_calls():
    runtime = FinanceRuntime(tenant_id="finance-test-react-seed")
    fx = {"from_currency": "USD", "to_currency": "EUR", "rate": 0.8785, "date": "2026-07-01"}
    seed_fx_cache_from_tool_calls(
        runtime,
        "What is the USD to EUR exchange rate today?",
        [{"tool": "fetch_exchange_rate", "ok": True, "data": fx}],
    )
    section = Section(
        section_id="fx",
        category_slug="fx_rates",
        content="What is the USD to EUR exchange rate today?",
        cache_policy=CachePolicy.REPLAY_SAFE,
    )
    decision = gate(
        "What is the USD to EUR exchange rate today?",
        section,
        runtime.cache,
        runtime.sidecar,
        coarse_threshold=0.88,
        verify_threshold=0.95,
    )
    assert decision.is_hit
    assert decision.value["rate"] == fx["rate"]


def test_react_path_seeds_canonical_phrases():
    runtime = FinanceRuntime(tenant_id="finance-test-react-seed-phrases")
    fx = {"from_currency": "USD", "to_currency": "EUR", "rate": 0.8785, "date": "2026-07-01"}
    seed_fx_cache_from_tool_calls(
        runtime,
        "What is the USD to EUR exchange rate today?",
        [{"tool": "fetch_exchange_rate", "ok": True, "data": fx}],
        extra_queries=["USD/EUR rate please", "Current dollar to euro FX rate"],
    )
    section = Section(
        section_id="fx",
        category_slug="fx_rates",
        content="USD/EUR rate please",
        cache_policy=CachePolicy.REPLAY_SAFE,
    )
    decision = gate(
        "USD/EUR rate please",
        section,
        runtime.cache,
        runtime.sidecar,
        coarse_threshold=0.88,
        verify_threshold=0.95,
    )
    assert decision.is_hit


@pytest.mark.live
@pytest.mark.skipif(not resolve_gemini_api_key(), reason="GEMINI_API_KEY not configured")
def test_react_graph_propagates_cache_score_on_hit():
    from chorusgraph.cache_gate import seed_cache_entry
    from chorusgraph.examples.finance_agent.patterns_graph import (
        build_react_graph,
        pattern_initial_state,
    )

    runtime = FinanceRuntime(tenant_id="finance-test-cache-score")
    compiled, _ = build_react_graph(runtime)
    fx = {"from_currency": "USD", "to_currency": "EUR", "rate": 0.8785, "date": "2026-07-01"}
    seed_cache_entry(
        runtime.cache,
        runtime.sidecar,
        query="What is the USD to EUR exchange rate today?",
        value=fx,
        category_slug="fx_rates",
        cache_policy="replay_safe",
    )
    result = compiled.invoke(pattern_initial_state("What is the USD to EUR exchange rate today?"))
    assert result.get("cache_hit") is True
    assert result.get("cache_score") is not None
    assert float(result["cache_score"]) > 0.0


@pytest.mark.live
@pytest.mark.skipif(not resolve_gemini_api_key(), reason="GEMINI_API_KEY not configured")
def test_finance_graph_end_to_end_with_ledger():
    compiled, runtime = build_finance_graph(FinanceRuntime(tenant_id="finance-test-e2e"))
    sink = SqliteLedgerSink(":memory:")
    wrapped = wrap(compiled, tenant_id=TENANT_ID, graph_id=GRAPH_ID, sink=sink)

    result = wrapped.invoke(initial_state("What is the USD to EUR exchange rate today?"))
    nodes = [s.node for s in wrapped.last_ledger.steps]
    assert "tool" in nodes
    assert "validator" in nodes
    assert result["response"]
    assert result["tool_calls"]
    assert result["tool_calls"][0]["ok"] is True
    assert result["validation"]["approved"] is True


@pytest.mark.live
@pytest.mark.skipif(not resolve_gemini_api_key(), reason="GEMINI_API_KEY not configured")
def test_two_turn_conversation_references_prior_context():
    compiled, runtime = build_finance_graph(FinanceRuntime(tenant_id="finance-test-2turn"))
    wrapped = wrap(
        compiled, tenant_id=TENANT_ID, graph_id=GRAPH_ID, sink=SqliteLedgerSink(":memory:")
    )

    r1 = wrapped.invoke(initial_state("What is the USD to EUR exchange rate today?"))
    history = [
        {"role": "user", "content": "What is the USD to EUR exchange rate today?"},
        {"role": "assistant", "content": r1["response"]},
    ]
    r2 = wrapped.invoke(initial_state("What about USD to GBP?", conversation_history=history))
    assert r2["tool_calls"]
    assert r2["tool_calls"][-1]["data"]["to_currency"] == "GBP"
    assert "GBP" in r2["response"].upper() or "pound" in r2["response"].lower()
