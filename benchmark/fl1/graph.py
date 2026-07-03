"""LangGraph ReAct finance agent — FL1 baseline."""

from __future__ import annotations

import operator
import re
import time
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from benchmark.shared.prompts import REACT_SYSTEM, VALIDATOR_SYSTEM, WRITER_SYSTEM
from chorusgraph.agents.react_utils import parse_react_json, tool_catalog
from chorusgraph.examples.finance_agent.nodes import _needs_fx_tool
from chorusgraph.nodes.tool import ToolRegistry, default_finance_registry
from chorusgraph.transforms.intent import needs_compound_tool

TENANT_ID = "benchmark-finance-a"
MAX_REACT_STEPS = 6


def _rate_in_text(rate: float, text: str) -> bool:
    if str(rate) in text:
        return True
    for decimals in (2, 3, 4, 5, 6):
        formatted = f"{rate:.{decimals}f}"
        if formatted in text or formatted.rstrip("0").rstrip(".") in text:
            return True
    nums = re.findall(r"\d+\.\d+", text)
    return any(abs(float(n) - rate) < 1e-4 for n in nums)


def _message_needs_tool(message: str) -> bool:
    return _needs_fx_tool(message) or needs_compound_tool(message)


class AgentState(TypedDict, total=False):
    message: str
    conversation_history: List[Dict[str, str]]
    scratchpad: str
    react_step: int
    pending_action: Optional[Dict[str, Any]]
    react_done: bool
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Any]
    tool_result: Optional[Dict[str, Any]]
    draft_response: str
    response: str
    validation: Dict[str, Any]
    rule_chain: Annotated[List[str], operator.add]


def fresh_turn_state(
    message: str,
    *,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Isolated per-task state — conversation history is the only cross-turn carryover."""
    return {
        "message": message,
        "conversation_history": list(conversation_history or []),
        "scratchpad": "",
        "react_step": 0,
        "react_done": False,
        "pending_action": None,
        "tool_calls": [],
        "tool_results": [],
        "tool_result": None,
        "draft_response": "",
        "response": "",
        "validation": {},
        "rule_chain": [],
    }


def build_langgraph_agent(
    *,
    registry: Optional[ToolRegistry] = None,
    gemini: Optional[InstrumentedGeminiClient] = None,
):
    registry = registry or default_finance_registry()
    gemini = gemini or InstrumentedGeminiClient()
    catalog = tool_catalog(registry)
    react_system = REACT_SYSTEM.format(tool_catalog=catalog)

    def react_node(state: AgentState) -> Dict[str, Any]:
        step = int(state.get("react_step") or 0)
        if step >= MAX_REACT_STEPS:
            return {"react_done": True, "rule_chain": ["react=max_steps"]}

        message = state.get("message") or ""
        scratchpad = state.get("scratchpad") or ""
        tool_calls_so_far = list(state.get("tool_calls") or [])
        needs_tool = _message_needs_tool(message)

        user = f"Question: {message}\n\nScratchpad:\n{scratchpad or '(empty)'}"
        raw = gemini.generate_json(react_system, user)
        parsed = parse_react_json(raw)
        action = parsed.get("action")
        finish = bool(parsed.get("finish"))
        has_action = bool(action and (action.get("tool") or action.get("name")))

        # Block finish-without-tool on FX/compound (model often tries to answer from parametric knowledge).
        if needs_tool and not tool_calls_so_far and finish and not has_action:
            finish = False

        update: Dict[str, Any] = {
            "react_step": step + 1,
            "pending_action": action if has_action else None,
            "react_done": False,
            "rule_chain": [f"react/thought step={step + 1}"],
        }
        if finish and not has_action:
            update["react_done"] = True
        elif finish and has_action and step + 1 < MAX_REACT_STEPS:
            update["react_done"] = False
        elif finish:
            update["react_done"] = True
        return update

    def tool_node(state: AgentState) -> Dict[str, Any]:
        action = state.get("pending_action") or {}
        tool = action.get("tool") or action.get("name") or "fetch_exchange_rate"
        args = dict(action.get("args") or action.get("arguments") or {})
        result = registry.run(tool, **args)
        tool_calls = list(state.get("tool_calls") or [])
        tool_calls.append(result.to_state_dict())
        obs = result.data if result.ok else f"ERROR: {result.error}"
        scratchpad = (state.get("scratchpad") or "") + f"\nAction: {tool}({args})\nObservation: {obs}\n"
        tool_results = list(state.get("tool_results") or [])
        if result.ok:
            tool_results.append(result.data)
        return {
            "scratchpad": scratchpad,
            "pending_action": None,
            "react_done": False,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "tool_result": result.data if result.ok else None,
            "rule_chain": [f"react/action {tool} ok={result.ok}"],
        }

    def writer_node(state: AgentState) -> Dict[str, Any]:
        message = state.get("message") or ""
        history = state.get("conversation_history") or []
        tool_result = state.get("tool_result")
        tool_results = state.get("tool_results") or []
        parts = [f"User question: {message}"]
        if tool_results:
            parts.append(f"Tool observations (authoritative): {tool_results}")
        elif tool_result:
            parts.append(f"Tool data (authoritative): {tool_result}")
        draft = gemini.generate(WRITER_SYSTEM, "\n".join(parts), history=history)
        return {"draft_response": draft, "rule_chain": ["writer=gemini_draft"]}

    def validator_node(state: AgentState) -> Dict[str, Any]:
        draft = state.get("draft_response") or ""
        tool_result = state.get("tool_result") or {}
        approved = True
        notes: List[str] = []

        if tool_result and "rate" in tool_result:
            rate = float(tool_result["rate"])
            if not _rate_in_text(rate, draft):
                notes.append(f"Draft missing explicit rate {rate}")
                approved = False

        if not approved and tool_result:
            user = (
                f"Draft:\n{draft}\n\nTool data:\n{tool_result}\n\n"
                "Rewrite the draft to include the exact tool rate. One short paragraph."
            )
            draft = gemini.generate(VALIDATOR_SYSTEM, user)
            if _rate_in_text(float(tool_result.get("rate", 0)), draft):
                approved = True
                notes.append("validator=rewrite_ok")

        message = state.get("message") or ""
        history = list(state.get("conversation_history") or [])
        if message:
            history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": draft})
        return {
            "validation": {"approved": approved, "notes": notes},
            "response": draft,
            "conversation_history": history,
            "rule_chain": [f"validator approved={approved}"],
        }

    def route_after_react(state: AgentState) -> str:
        if state.get("pending_action"):
            return "tool"
        if state.get("react_done"):
            return "writer"
        step = int(state.get("react_step") or 0)
        if step >= MAX_REACT_STEPS:
            return "writer"
        return "react"

    def route_after_tool(state: AgentState) -> str:
        if int(state.get("react_step") or 0) >= MAX_REACT_STEPS:
            return "writer"
        return "react"

    graph = StateGraph(AgentState)
    graph.add_node("react", react_node)
    graph.add_node("tool", tool_node)
    graph.add_node("writer", writer_node)
    graph.add_node("validator", validator_node)

    graph.add_edge(START, "react")
    graph.add_conditional_edges(
        "react",
        route_after_react,
        {"tool": "tool", "writer": "writer", "react": "react"},
    )
    graph.add_conditional_edges("tool", route_after_tool, {"react": "react", "writer": "writer"})
    graph.add_edge("writer", "validator")
    graph.add_edge("validator", END)

    # No checkpointer — runner owns conversation_history; MemorySaver was leaking react state across tasks.
    compiled = graph.compile()
    return compiled, gemini, None


def run_task(
    message: str,
    *,
    compiled,
    gemini: InstrumentedGeminiClient,
    thread_id: str = "",
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Run one benchmark task through FL1."""
    del thread_id  # kept for runner API compatibility
    gemini.reset_usage()
    started = time.perf_counter()
    state = fresh_turn_state(message, conversation_history=conversation_history)
    try:
        result = compiled.invoke(state)
        latency_ms = int((time.perf_counter() - started) * 1000)
        result["_latency_ms"] = latency_ms
        result["_llm_usage"] = gemini.usage
        return result
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "response": "",
            "error": str(exc),
            "_latency_ms": latency_ms,
            "_llm_usage": gemini.usage,
            "tool_calls": [],
        }
