"""FL2 — LangGraph finance multi-agent baseline (growing text handoffs)."""

from __future__ import annotations

import json
import operator
import time
from typing import Annotated, Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph

from benchmark.finance_multiagent_shared import (
    FinanceMultiAgentState,
    heuristic_tool_plan,
    record_hop,
    validate_draft,
)
from benchmark.fl2.prompts import RESEARCHER_SYSTEM
from benchmark.measure import TaskMeasurement, score_task_success
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from benchmark.shared.prompts import WRITER_SYSTEM
from benchmark.workload import WorkloadTask
from chorusgraph.nodes.tool import ToolRegistry, default_finance_registry


def _parse_researcher_json(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
        else:
            return {}
    return data if isinstance(data, dict) else {}


def build_finance_graph_fl2(
    *,
    registry: Optional[ToolRegistry] = None,
    gemini: Optional[InstrumentedGeminiClient] = None,
):
    registry = registry or default_finance_registry()
    gemini = gemini or InstrumentedGeminiClient()

    def researcher_node(state: FinanceMultiAgentState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        message = state.get("message") or ""
        history = state.get("conversation_history") or []
        user = f"Question: {message}\n\nPrior context:\n{state.get('context') or '(none)'}"
        raw = gemini.generate(RESEARCHER_SYSTEM, user, history=history)
        parsed = _parse_researcher_json(raw)
        tools = parsed.get("tools") if isinstance(parsed.get("tools"), list) else []
        plan = str(parsed.get("plan") or "")
        if not tools:
            fallback, fallback_plan = heuristic_tool_plan(message)
            tools = fallback
            if not plan:
                plan = fallback_plan
        tool_plan = [t for t in tools if isinstance(t, dict) and t.get("tool")]
        context = (state.get("context") or "") + f"\n\nResearcher:\n{plan}"
        return {
            "research_plan": plan,
            "tool_plan": tool_plan,
            "needs_tool": bool(tool_plan),
            "context": context.strip(),
            **record_hop(state, "researcher", started, gemini),
        }

    def tool_node(state: FinanceMultiAgentState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        tool_plan = list(state.get("tool_plan") or [])
        if not tool_plan:
            return record_hop(state, "tool", started, gemini, tools=0)

        tool_calls: List[Dict[str, Any]] = list(state.get("tool_calls") or [])
        tool_results: List[Any] = list(state.get("tool_results") or [])
        observations: List[str] = []
        primary: Optional[Dict[str, Any]] = None

        for item in tool_plan:
            name = str(item.get("tool") or "fetch_exchange_rate")
            args = dict(item.get("args") or {})
            result = registry.run(name, **args)
            tool_calls.append(result.to_state_dict())
            if result.ok:
                tool_results.append(result.data)
                primary = result.data if primary is None else primary
                observations.append(f"{name}({args}) -> {result.data}")
            else:
                observations.append(f"{name} ERROR: {result.error}")

        context = (state.get("context") or "") + "\n\nTool:\n" + "\n".join(observations)
        return {
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "tool_result": primary,
            "context": context.strip(),
            **record_hop(state, "tool", started, gemini, tools=len(tool_plan)),
        }

    def writer_node(state: FinanceMultiAgentState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        message = state.get("message") or ""
        history = state.get("conversation_history") or []
        user = f"User question: {message}\n\nAccumulated context:\n{state.get('context') or '(none)'}"
        draft = gemini.generate(WRITER_SYSTEM, user, history=history)
        context = (state.get("context") or "") + f"\n\nWriter draft:\n{draft[:400]}"
        return {
            "draft_response": draft,
            "context": context.strip(),
            **record_hop(state, "writer", started, gemini),
        }

    def validator_node(state: FinanceMultiAgentState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        draft = state.get("draft_response") or ""
        tool_result = state.get("tool_result")
        if state.get("tool_results") and not tool_result:
            tool_result = state["tool_results"][0] if state["tool_results"] else None
        response, validation = validate_draft(draft, tool_result, gemini)

        message = state.get("message") or ""
        history = list(state.get("conversation_history") or [])
        if message:
            history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})

        return {
            "response": response,
            "validation": validation,
            "conversation_history": history,
            **record_hop(state, "validator", started, gemini),
        }

    graph = StateGraph(FinanceMultiAgentState)
    graph.add_node("researcher", researcher_node)
    graph.add_node("tool", tool_node)
    graph.add_node("writer", writer_node)
    graph.add_node("validator", validator_node)
    graph.add_edge(START, "researcher")
    graph.add_edge("researcher", "tool")
    graph.add_edge("tool", "writer")
    graph.add_edge("writer", "validator")
    graph.add_edge("validator", END)
    return graph.compile(), gemini


class FL2Runner:
    """LangGraph finance multi-agent — researcher → tool → writer → validator."""

    def __init__(self) -> None:
        self._compiled, self._gemini = build_finance_graph_fl2()
        self._histories: Dict[str, List[Dict[str, str]]] = {}

    def run(self, task: WorkloadTask) -> TaskMeasurement:
        history = self._histories.get(task.session_id, [])
        if task.cross_session_recall:
            history = []

        self._gemini.reset_usage()
        started = time.perf_counter()
        try:
            result = self._compiled.invoke(
                {
                    "task": task,
                    "message": task.message,
                    "conversation_history": history,
                    "context": "",
                    "tool_calls": [],
                    "tool_results": [],
                    "hop_metrics": [],
                }
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            if result.get("conversation_history") and not task.cross_session_recall:
                self._histories[task.session_id] = list(result["conversation_history"])

            hop_metrics = list(result.get("hop_metrics") or [])
            llm_calls = sum(h.llm_calls for h in hop_metrics)
            tokens_in = sum(h.tokens_in for h in hop_metrics)
            tokens_out = sum(h.tokens_out for h in hop_metrics)

            return TaskMeasurement(
                task_id=task.task_id,
                session_id=task.session_id,
                container="FL2",
                message=task.message,
                variant=task.variant,
                latency_ms=latency_ms,
                llm_calls=llm_calls,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=(tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000,
                task_success=score_task_success(
                    message=task.message,
                    answer=result.get("response") or "",
                    error=result.get("error"),
                    validation=result.get("validation"),
                    canonical_id=task.canonical_id,
                    tool_result=result.get("tool_result"),
                    variant=task.variant,
                ),
                answer=(result.get("response") or "")[:2000],
                tool_calls=len(result.get("tool_calls") or []),
                category_slug=task.category_slug,
                memory_cortex_group=task.memory_cortex_group,
                cross_session_recall=task.cross_session_recall or None,
                hop_metrics=[h.__dict__ for h in hop_metrics],
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            usage = self._gemini.usage
            return TaskMeasurement(
                task_id=task.task_id,
                session_id=task.session_id,
                container="FL2",
                message=task.message,
                variant=task.variant,
                latency_ms=latency_ms,
                llm_calls=usage.llm_calls,
                tokens_in=usage.tokens_in,
                tokens_out=usage.tokens_out,
                cost_usd=usage.cost_usd,
                task_success=False,
                answer="",
                error=str(exc),
                tool_calls=0,
                category_slug=task.category_slug,
                memory_cortex_group=task.memory_cortex_group,
                cross_session_recall=task.cross_session_recall or None,
            )
