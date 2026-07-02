"""Container F — ChorusGraph finance multi-agent (envelope + cache gate)."""

from __future__ import annotations

import json
import operator
import time
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph
from prismlang import PrismEnvelope

from benchmark.container_e.prompts import RESEARCHER_SYSTEM
from benchmark.container_e.runner import _parse_researcher_json
from benchmark.container_f.artifacts import (
    compact_draft,
    compact_json,
    compact_plan,
    compact_tool,
    envelope_handoff,
    store_envelope_artifact,
)
from benchmark.finance_multiagent_shared import (
    FinanceMultiAgentState,
    heuristic_tool_plan,
    record_hop,
    validate_draft,
)
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from benchmark.shared.prompts import WRITER_SYSTEM
from benchmark.thresholds import measured_thresholds
from benchmark.workload import CANONICAL_QUERIES, WorkloadTask
from chorusgraph.examples.finance_agent.nodes import (
    make_cache_gate_handler,
    make_vector_ingress_handler,
    seed_fx_cache_from_tool_calls,
)
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime
from chorusgraph.memory.recall import format_evidence_for_llm
from chorusgraph.transforms.projector import project_text
from chorusgraph.transforms.templates import try_template_draft

TENANT_ID = "benchmark-finance-f"
BENCHMARK_CORTEX_ROOT = Path(".chorusgraph/benchmark_sessions_f")


class FinanceVectorState(FinanceMultiAgentState, total=False):
    raw_embedding_384: List[float]
    query_vector_64: List[float]
    prism_sequence: Annotated[List[PrismEnvelope], operator.add]
    vector_hops: Annotated[List[Dict[str, Any]], operator.add]
    cache_score: Optional[float]
    cache_coarse_score: Optional[float]
    cache_verify_score: Optional[float]


def _envelope_update(runtime: FinanceRuntime, hop: str, artifact: Dict[str, Any]) -> Dict[str, Any]:
    if runtime.cache is None:
        return {}
    _, envelope = project_text(runtime.cache, compact_json(artifact))
    store_envelope_artifact(runtime, envelope.envelope_id, artifact)
    return {
        "prism_sequence": [envelope],
        "latest_envelope_id": envelope.envelope_id,
        "vector_hops": [
            {"hop": hop, "vector_dim": len(envelope.vector), "envelope_id": envelope.envelope_id}
        ],
    }


def make_f_nodes(gemini: InstrumentedGeminiClient, runtime: FinanceRuntime) -> Dict[str, Any]:
    def researcher_node(state: FinanceVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        message = state.get("message") or ""

        if state.get("cache_hit") and state.get("tool_result"):
            artifact = {
                "plan": "Use cached FX data.",
                "tools": [],
                "from_cache": True,
            }
            hop_artifacts = {"researcher": artifact}
            return {
                "research_plan": artifact["plan"],
                "tool_plan": [],
                "needs_tool": False,
                **_envelope_update(runtime, "researcher", artifact),
                **record_hop(state, "researcher", started, gemini),
            }

        user = envelope_handoff(
            hop="researcher",
            envelope_id=state.get("latest_envelope_id"),
            hop_input={"question": message[:300]},
        )
        raw = gemini.generate(RESEARCHER_SYSTEM, user)
        parsed = _parse_researcher_json(raw)
        tools = parsed.get("tools") if isinstance(parsed.get("tools"), list) else []
        plan = str(parsed.get("plan") or "")
        if not tools:
            fallback, fallback_plan = heuristic_tool_plan(message)
            tools = fallback
            if not plan:
                plan = fallback_plan
        tool_plan = [t for t in tools if isinstance(t, dict) and t.get("tool")]
        artifact = {"plan": plan, "tools": tool_plan}
        return {
            "research_plan": plan,
            "tool_plan": tool_plan,
            "needs_tool": bool(tool_plan),
            **_envelope_update(runtime, "researcher", artifact),
            **record_hop(state, "researcher", started, gemini),
        }

    def tool_node(state: FinanceVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()

        if state.get("cache_hit") and state.get("tool_result"):
            artifact = {
                "primary": state.get("tool_result"),
                "results": list(state.get("tool_results") or [state.get("tool_result")]),
                "n_calls": 0,
                "from_cache": True,
            }
            return {
                **_envelope_update(runtime, "tool", artifact),
                **record_hop(state, "tool", started, gemini, tools=0),
            }

        tool_plan = list(state.get("tool_plan") or [])
        tool_calls: List[Dict[str, Any]] = list(state.get("tool_calls") or [])
        tool_results: List[Any] = list(state.get("tool_results") or [])
        primary: Optional[Dict[str, Any]] = None

        for item in tool_plan:
            name = str(item.get("tool") or "fetch_exchange_rate")
            args = dict(item.get("args") or {})
            result = runtime.tool_registry.run(name, **args)
            tool_calls.append(result.to_state_dict())
            if result.ok:
                tool_results.append(result.data)
                primary = result.data if primary is None else primary
                if name == "fetch_exchange_rate":
                    seed_fx_cache_from_tool_calls(
                        runtime,
                        state.get("message") or "",
                        [result.to_state_dict()],
                        extra_queries=list(state.get("cache_seed_phrases") or []),
                    )

        artifact = {
            "primary": primary or {},
            "results": tool_results,
            "n_calls": len(tool_plan),
        }
        return {
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "tool_result": primary,
            **_envelope_update(runtime, "tool", artifact),
            **record_hop(state, "tool", started, gemini, tools=len(tool_plan)),
        }

    def writer_node(state: FinanceVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        message = state.get("message") or ""
        history = state.get("conversation_history") or []
        tool_result = state.get("tool_result")
        tool_results = list(state.get("tool_results") or [])

        memory_ctx = (
            runtime.cortex.recall_structured(message, cache=runtime.cache)
            if runtime.cortex
            else None
        )
        draft = try_template_draft(
            message=message,
            tool_result=tool_result,
            tool_results=tool_results,
            memory_ctx=memory_ctx,
        )
        used_llm = draft is None
        if draft is None:
            user = envelope_handoff(
                hop="writer",
                envelope_id=state.get("latest_envelope_id"),
                hop_input={
                    "question": message[:200],
                    "tool": compact_tool({"primary": tool_result, "results": tool_results, "n_calls": len(tool_results)}),
                    "plan": compact_plan({"plan": state.get("research_plan"), "tools": state.get("tool_plan")}),
                },
            )
            if memory_ctx:
                block = format_evidence_for_llm(memory_ctx)
                if block:
                    user = user + "\n" + block[:500]
            draft = gemini.generate(WRITER_SYSTEM, user, history=history)

        artifact = {"draft": draft, "used_llm": used_llm}
        update: Dict[str, Any] = {
            "draft_response": draft,
            **_envelope_update(runtime, "writer", artifact),
            **record_hop(state, "writer", started, gemini),
        }
        if memory_ctx:
            update.update(memory_ctx.to_memory_state())
        return update

    def validator_node(state: FinanceVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        draft = state.get("draft_response") or ""
        tool_result = state.get("tool_result")
        if state.get("tool_results") and not tool_result:
            tool_result = state["tool_results"][0]
        response, validation = validate_draft(draft, tool_result, gemini)

        message = state.get("message") or ""
        history = list(state.get("conversation_history") or [])
        if message:
            history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})

        artifact = {"approved": validation.get("approved"), "notes": validation.get("notes") or []}
        return {
            "response": response,
            "validation": validation,
            "conversation_history": history,
            **_envelope_update(runtime, "validator", artifact),
            **record_hop(state, "validator", started, gemini),
        }

    return {
        "researcher": researcher_node,
        "tool": tool_node,
        "writer": writer_node,
        "validator": validator_node,
    }


def build_finance_graph_f(
    *,
    runtime: Optional[FinanceRuntime] = None,
    gemini: Optional[InstrumentedGeminiClient] = None,
):
    runtime = runtime or FinanceRuntime(tenant_id=TENANT_ID)
    gemini = gemini or InstrumentedGeminiClient()
    runtime.gemini = gemini
    thresholds = measured_thresholds()
    nodes = make_f_nodes(gemini, runtime)
    ingress = make_vector_ingress_handler(runtime)
    cache_gate = make_cache_gate_handler(
        runtime,
        coarse_threshold=thresholds.coarse,
        verify_threshold=thresholds.verify_for("fx_rates"),
    )

    graph = StateGraph(FinanceVectorState)

    def vector_ingress_node(state: FinanceVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        update = ingress({"message": state.get("message") or ""})
        return {
            **update,
            **record_hop(state, "vector_ingress", started, gemini),
        }

    def cache_gate_node(state: FinanceVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        update = cache_gate(state)
        return {
            **update,
            **record_hop(state, "cache_gate", started, gemini),
        }

    graph.add_node("vector_ingress", vector_ingress_node)
    graph.add_node("cache_gate", cache_gate_node)
    for name in ("researcher", "tool", "writer", "validator"):
        graph.add_node(name, nodes[name])

    graph.add_edge(START, "vector_ingress")
    graph.add_edge("vector_ingress", "cache_gate")
    graph.add_edge("cache_gate", "researcher")
    graph.add_edge("researcher", "tool")
    graph.add_edge("tool", "writer")
    graph.add_edge("writer", "validator")
    graph.add_edge("validator", END)
    return graph.compile(), gemini, runtime
