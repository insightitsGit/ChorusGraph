"""FL1 LangGraph baseline — H11 tool-routing regression tests."""

from __future__ import annotations

from benchmark.fl1.graph import build_langgraph_agent, fresh_turn_state, run_task
from benchmark.shared.stub_gemini import StubGemini
from benchmark.workload import CANONICAL_QUERIES

FX_ACTION = {
    "tool": "fetch_exchange_rate",
    "args": {"from_currency": "USD", "to_currency": "EUR"},
}


def test_fresh_turn_state_clears_react_fields():
    state = fresh_turn_state("hello", conversation_history=[{"role": "user", "content": "prior"}])
    assert state["scratchpad"] == ""
    assert state["react_done"] is False
    assert state["tool_calls"] == []
    assert state["tool_result"] is None
    assert len(state["conversation_history"]) == 1


def test_fx_task_calls_tool_after_early_finish_blocked():
    stub = StubGemini(
        [
            {"thought": "I know this", "action": None, "finish": True},
            {"thought": "fetch", "action": FX_ACTION, "finish": False},
            {"thought": "done", "action": None, "finish": True},
        ],
        writer_text="1 USD = 0.87727 EUR per tool.",
    )
    compiled, gemini, _ = build_langgraph_agent(gemini=stub)
    result = run_task(
        CANONICAL_QUERIES["usd_eur"][0],
        compiled=compiled,
        gemini=gemini,
    )
    assert len(result.get("tool_calls") or []) >= 1
    assert stub._react_i >= 2


def test_second_task_in_session_still_calls_tool():
    """Regression: MemorySaver + stale react_done caused task 2+ to skip tools (H11 root cause c)."""
    stub = StubGemini(
        [
            {"thought": "fetch", "action": FX_ACTION, "finish": False},
            {"thought": "done", "action": None, "finish": True},
        ],
        writer_text="1 USD = 0.87727 EUR.",
    )
    compiled, gemini, _ = build_langgraph_agent(gemini=stub)

    history: list[dict[str, str]] = []
    tool_counts: list[int] = []
    for message in (CANONICAL_QUERIES["usd_eur"][0], CANONICAL_QUERIES["usd_gbp"][0]):
        stub._react_i = 0
        result = run_task(message, compiled=compiled, gemini=gemini, conversation_history=history)
        tool_counts.append(len(result.get("tool_calls") or []))
        history = list(result.get("conversation_history") or history)

    assert tool_counts[0] >= 1
    assert tool_counts[1] >= 1


def test_route_loops_react_when_no_action_and_not_done():
    stub = StubGemini(
        [
            {"thought": "hmm", "action": None, "finish": False},
            {"thought": "fetch", "action": FX_ACTION, "finish": False},
            {"thought": "done", "action": None, "finish": True},
        ],
    )
    compiled, gemini, _ = build_langgraph_agent(gemini=stub)
    result = run_task("USD/EUR rate please", compiled=compiled, gemini=gemini)
    assert len(result.get("tool_calls") or []) >= 1
    assert stub._react_i >= 2
