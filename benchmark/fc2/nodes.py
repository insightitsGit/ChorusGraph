"""FC2 — ChorusGraph finance multi-agent (envelope + cache gate)."""

from __future__ import annotations

import operator
import time
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import dict_node_adapter
from prismlang import PrismEnvelope

from benchmark.fl2.prompts import RESEARCHER_SYSTEM
from benchmark.fl2.runner import _parse_researcher_json
from benchmark.fc2.artifacts import (
    compact_plan,
    compact_tool,
    envelope_handoff,
    store_envelope_artifact,
)
from benchmark.fc2.cache_helpers import collect_cached_tool_results
from benchmark.fc2.trace import trace_event
from benchmark.finance_multiagent_shared import (
    FinanceMultiAgentState,
    heuristic_tool_plan,
    record_hop,
    validate_draft,
)
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from benchmark.shared.prompts import WRITER_SYSTEM
from benchmark.thresholds import measured_thresholds
from chorusgraph.examples.finance_agent.nodes import (
    make_cache_gate_handler,
    make_vector_ingress_handler,
    seed_fx_cache_from_tool_calls,
)
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime
from chorusgraph.memory.recall import format_evidence_for_llm
from chorusgraph.transforms.projector import project_from_raw, project_text, raw_from_state
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
    cache_decision: Optional[str]


def _trace_ids(state: FinanceMultiAgentState) -> tuple[str, str]:
    task = state.get("task")
    if task is not None:
        return str(getattr(task, "task_id", "") or ""), str(getattr(task, "session_id", "") or "")
    return "", ""


def _hop_trace(
    state: FinanceVectorState,
    hop: str,
    started: float,
    gemini: InstrumentedGeminiClient,
    **extra: Any,
) -> None:
    task_id, session_id = _trace_ids(state)
    trace_event(
        "hop_end",
        task_id=task_id,
        session_id=session_id,
        hop=hop,
        latency_ms=int((time.perf_counter() - started) * 1000),
        llm_calls=gemini.usage.llm_calls,
        tokens_in=gemini.usage.tokens_in,
        tokens_out=gemini.usage.tokens_out,
        cache_hit=state.get("cache_hit"),
        **extra,
    )


def route_after_cache_fc2(state: FinanceVectorState) -> str:
    """F1: skip researcher+tool on verified cache hit (mirror FC1)."""
    hit = bool(state.get("cache_hit") and state.get("tool_result"))
    route = "writer" if hit else "researcher"
    task_id, session_id = _trace_ids(state)
    trace_event(
        "route_after_cache",
        task_id=task_id,
        session_id=session_id,
        route=route,
        cache_hit=state.get("cache_hit"),
        cache_decision=state.get("cache_decision"),
        cache_score=state.get("cache_score"),
        has_tool_result=state.get("tool_result") is not None,
        tool_results_count=len(state.get("tool_results") or []),
    )
    return route


def _envelope_update(
    runtime: FinanceRuntime,
    hop: str,
    artifact: Dict[str, Any],
    *,
    state: Optional[FinanceVectorState] = None,
    skip_embed: bool = False,
) -> Dict[str, Any]:
    """F2: reuse ingress raw_384; skip re-embed entirely on cache-hit fast path."""
    if runtime.cache is None:
        return {}
    task_id, session_id = _trace_ids(state or {})
    raw_arr = raw_from_state(state) if state else None
    if skip_embed and raw_arr is not None:
        _, envelope = project_from_raw(runtime.cache, raw_arr)
        embed_mode = "reuse_ingress"
    else:
        from benchmark.fc2.artifacts import compact_json

        _, envelope = project_text(runtime.cache, compact_json(artifact), raw_384=raw_arr)
        embed_mode = "reuse_raw" if raw_arr is not None else "full_embed"
    store_envelope_artifact(runtime, envelope.envelope_id, artifact)
    trace_event(
        "envelope_write",
        task_id=task_id,
        session_id=session_id,
        hop=hop,
        envelope_id=envelope.envelope_id,
        embed_mode=embed_mode,
        artifact_keys=sorted(artifact.keys()),
    )
    return {
        "prism_sequence": [envelope],
        "latest_envelope_id": envelope.envelope_id,
        "vector_hops": [
            {"hop": hop, "vector_dim": len(envelope.vector), "envelope_id": envelope.envelope_id}
        ],
    }


def _writer_user_prompt(
    *,
    state: FinanceVectorState,
    runtime: FinanceRuntime,
    message: str,
    tool_result: Optional[Dict[str, Any]],
    tool_results: List[Any],
    memory_ctx: Any,
) -> str:
    """F6: on cache hit use FC1 plain tool context; else envelope handoff."""
    task_id, session_id = _trace_ids(state)
    if state.get("cache_hit"):
        parts = [f"User question: {message}"]
        if tool_results:
            parts.append(f"Tool observations (authoritative): {tool_results}")
        elif tool_result:
            parts.append(f"Tool data (authoritative): {tool_result}")
        prompt = "\n".join(parts)
        trace_event(
            "writer_prompt",
            task_id=task_id,
            session_id=session_id,
            hop="writer",
            mode="cache_hit_plain",
            tool_results_count=len(tool_results),
        )
        return prompt

    user = envelope_handoff(
        hop="writer",
        envelope_id=state.get("latest_envelope_id"),
        hop_input={
            "question": message[:200],
            "tool": compact_tool(
                {"primary": tool_result, "results": tool_results, "n_calls": len(tool_results)}
            ),
            "plan": compact_plan({"plan": state.get("research_plan"), "tools": state.get("tool_plan")}),
        },
        runtime=runtime,
        task_id=task_id,
        session_id=session_id,
    )
    if memory_ctx:
        block = format_evidence_for_llm(memory_ctx)
        if block:
            user = user + "\n" + block[:500]
    trace_event(
        "writer_prompt",
        task_id=task_id,
        session_id=session_id,
        hop="writer",
        mode="envelope_handoff",
        tool_results_count=len(tool_results),
    )
    return user


def make_f_nodes(gemini: InstrumentedGeminiClient, runtime: FinanceRuntime) -> Dict[str, Any]:
    def researcher_node(state: FinanceVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        message = state.get("message") or ""
        task_id, session_id = _trace_ids(state)

        if state.get("cache_hit") and state.get("tool_result"):
            artifact = {"plan": "Use cached FX data.", "tools": [], "from_cache": True}
            out = {
                "research_plan": artifact["plan"],
                "tool_plan": [],
                "needs_tool": False,
                **_envelope_update(
                    runtime, "researcher", artifact, state=state, skip_embed=True
                ),
                **record_hop(state, "researcher", started, gemini),
            }
            _hop_trace(state, "researcher", started, gemini, skipped=True, reason="cache_hit")
            return out

        user = envelope_handoff(
            hop="researcher",
            envelope_id=state.get("latest_envelope_id"),
            hop_input={"question": message[:300]},
            runtime=runtime,
            task_id=task_id,
            session_id=session_id,
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
        out = {
            "research_plan": plan,
            "tool_plan": tool_plan,
            "needs_tool": bool(tool_plan),
            **_envelope_update(runtime, "researcher", artifact, state=state),
            **record_hop(state, "researcher", started, gemini),
        }
        _hop_trace(
            state,
            "researcher",
            started,
            gemini,
            tool_plan_len=len(tool_plan),
            used_heuristic=not parsed.get("tools"),
        )
        return out

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
            out = {
                **_envelope_update(runtime, "tool", artifact, state=state, skip_embed=True),
                **record_hop(state, "tool", started, gemini, tools=0),
            }
            _hop_trace(state, "tool", started, gemini, skipped=True, reason="cache_hit")
            return out

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

        artifact = {"primary": primary or {}, "results": tool_results, "n_calls": len(tool_plan)}
        out = {
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "tool_result": primary,
            **_envelope_update(runtime, "tool", artifact, state=state),
            **record_hop(state, "tool", started, gemini, tools=len(tool_plan)),
        }
        _hop_trace(state, "tool", started, gemini, tool_calls=len(tool_plan), results=len(tool_results))
        return out

    def writer_node(state: FinanceVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        message = state.get("message") or ""
        history = state.get("conversation_history") or []
        tool_result = state.get("tool_result")
        tool_results = list(state.get("tool_results") or [])
        if not tool_results and tool_result:
            tool_results = [tool_result]

        raw_arr = raw_from_state(state)
        memory_ctx = (
            runtime.cortex.recall_structured(
                message, cache=runtime.cache, raw_384=raw_arr
            )
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
            user = _writer_user_prompt(
                state=state,
                runtime=runtime,
                message=message,
                tool_result=tool_result,
                tool_results=tool_results,
                memory_ctx=memory_ctx,
            )
            draft = gemini.generate(WRITER_SYSTEM, user, history=history)

        artifact = {"draft": draft, "used_llm": used_llm}
        skip_embed = bool(state.get("cache_hit"))
        update: Dict[str, Any] = {
            "draft_response": draft,
            **_envelope_update(
                runtime, "writer", artifact, state=state, skip_embed=skip_embed
            ),
            **record_hop(state, "writer", started, gemini),
        }
        if memory_ctx:
            update.update(memory_ctx.to_memory_state())
        _hop_trace(
            state,
            "writer",
            started,
            gemini,
            used_template=not used_llm,
            draft_len=len(draft or ""),
        )
        return update

    def validator_node(state: FinanceVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        draft = state.get("draft_response") or ""
        tool_result = state.get("tool_result")
        tool_results = list(state.get("tool_results") or [])
        if tool_results and not tool_result:
            tool_result = tool_results[0]
        response, validation = validate_draft(draft, tool_result, gemini)

        message = state.get("message") or ""
        history = list(state.get("conversation_history") or [])
        if message:
            history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})

        artifact = {"approved": validation.get("approved"), "notes": validation.get("notes") or []}
        out = {
            "response": response,
            "validation": validation,
            "conversation_history": history,
            **_envelope_update(
                runtime,
                "validator",
                artifact,
                state=state,
                skip_embed=bool(state.get("cache_hit")),
            ),
            **record_hop(state, "validator", started, gemini),
        }
        _hop_trace(
            state,
            "validator",
            started,
            gemini,
            approved=validation.get("approved"),
            validator_llm=gemini.usage.llm_calls > 0,
        )
        return out

    return {
        "researcher": researcher_node,
        "tool": tool_node,
        "writer": writer_node,
        "validator": validator_node,
    }


def build_finance_graph_fc2(
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
    cache_gate_base = make_cache_gate_handler(
        runtime,
        coarse_threshold=thresholds.coarse,
        verify_threshold=thresholds.verify_for("fx_rates"),
    )

    graph = Graph(tenant_id=TENANT_ID, graph_id="finance-fc2")

    def vector_ingress_node(state: FinanceVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        update = ingress({"message": state.get("message") or ""})
        out = {**update, **record_hop(state, "vector_ingress", started, gemini)}
        _hop_trace(
            state,
            "vector_ingress",
            started,
            gemini,
            has_raw=bool(update.get("raw_embedding_384")),
            vector_dim=len(update.get("query_vector_64") or []),
        )
        return out

    def cache_gate_node(state: FinanceVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        update = dict(cache_gate_base(state))
        message = state.get("message") or ""

        # F5: expand single cache hit into tool_results for multi-FX compare.
        if update.get("cache_hit") and update.get("tool_result"):
            primary = update["tool_result"]
            tool_results = collect_cached_tool_results(runtime, message, primary)
            update["tool_results"] = tool_results
            if tool_results:
                update["tool_result"] = tool_results[0]

        out = {**update, **record_hop(state, "cache_gate", started, gemini)}
        task_id, session_id = _trace_ids(state)
        trace_event(
            "cache_gate_result",
            task_id=task_id,
            session_id=session_id,
            hop="cache_gate",
            cache_hit=update.get("cache_hit"),
            cache_decision=update.get("cache_decision"),
            cache_score=update.get("cache_score"),
            tool_results_count=len(update.get("tool_results") or []),
            session_cache_keys=len(runtime.session_tool_cache),
        )
        _hop_trace(
            state,
            "cache_gate",
            started,
            gemini,
            gate_cache_hit=update.get("cache_hit"),
            tool_results_count=len(update.get("tool_results") or []),
        )
        return out

    graph.add_node(
        "vector_ingress",
        dict_node_adapter(vector_ingress_node, hop="vector_ingress"),
    )
    graph.add_node("cache_gate", dict_node_adapter(cache_gate_node, hop="cache_gate"))
    for name in ("researcher", "tool", "writer", "validator"):
        graph.add_node(name, dict_node_adapter(nodes[name], hop=name))

    graph.add_edge(START, "vector_ingress")
    graph.add_edge("vector_ingress", "cache_gate")
    graph.add_conditional_edges(
        "cache_gate",
        route_after_cache_fc2,
        {"writer": "writer", "researcher": "researcher"},
    )
    graph.add_edge("researcher", "tool")
    graph.add_edge("tool", "writer")
    graph.add_edge("writer", "validator")
    graph.add_edge("validator", END)
    return graph.compile(), gemini, runtime
