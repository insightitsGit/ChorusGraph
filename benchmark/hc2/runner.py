"""HC2 — ChorusGraph multi-agent healthcare (cache gate + envelope handoffs)."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from benchmark.hl2.runner import _record_hop
from benchmark.healthcare.cache_gate import gate_healthcare_case
from benchmark.hc2.cache_helpers import apply_cache_payload, cache_query_key, cache_seed_phrases
from benchmark.hc2.nodes import make_hc2_nodes, route_after_cache_hc2
from benchmark.hc2.runtime import make_healthcare_envelope_runtime
from benchmark.hc2.trace import clear_trace, trace_event, trace_path
from benchmark.healthcare_workload import PIPELINE_AGENTS, HealthcareCase
from benchmark.multiagent_measure import MultiAgentMeasurement, hop_names, score_healthcare_answer, totals_from_hops
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from benchmark.thresholds import measured_thresholds
from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import dict_node_adapter
from chorusgraph.examples.finance_agent.nodes import make_vector_ingress_handler
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime
from chorusgraph.transforms.projector import raw_from_state, vector_64_from_state

from benchmark.hc2.state import HealthcareVectorState

HC2_GRAPH_ID = "healthcare-hc2"
HC2_TENANT_ID = "benchmark-healthcare-hc2"


def _make_healthcare_cache_gate_handler(
    runtime: FinanceRuntime,
    *,
    coarse_threshold: float,
    verify_threshold: float,
):
    """Clinical cache gate — CacheProfile global facts (H21)."""

    def cache_gate_node(state: HealthcareVectorState) -> Dict[str, Any]:
        case = state.get("case")
        if case is None:
            return {"cache_hit": False, "cache_decision": "miss"}
        decision = gate_healthcare_case(
            runtime,
            case,
            coarse_threshold=coarse_threshold,
            verify_threshold=verify_threshold,
            raw_embedding_384=raw_from_state(state),
            projected_vector_64=vector_64_from_state(state),
        )
        update: Dict[str, Any] = {
            "cache_hit": decision.is_hit,
            "cache_score": decision.verify_score or decision.coarse_score,
            "cache_coarse_score": decision.coarse_score,
            "cache_verify_score": decision.verify_score,
            "cache_decision": decision.kind.value,
        }
        if decision.is_hit and decision.value:
            update = apply_cache_payload(update, decision.value)
        return update

    return cache_gate_node


def build_healthcare_graph_hc2(
    *,
    depth: int,
    runtime: Optional[FinanceRuntime] = None,
    gemini: Optional[InstrumentedGeminiClient] = None,
):
    runtime = runtime or make_healthcare_envelope_runtime()
    gemini = gemini or InstrumentedGeminiClient()
    runtime.gemini = gemini
    nodes = make_hc2_nodes(gemini, runtime)
    agents = PIPELINE_AGENTS[depth]
    ingress = make_vector_ingress_handler(runtime)
    thresholds = measured_thresholds()
    cache_gate_base = _make_healthcare_cache_gate_handler(
        runtime,
        coarse_threshold=thresholds.coarse,
        verify_threshold=thresholds.verify_for("clinical_guidelines"),
    )

    graph = Graph(tenant_id=HC2_TENANT_ID, graph_id=HC2_GRAPH_ID)

    def vector_ingress_node(state: HealthcareVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        case = state["case"]
        query = cache_query_key(case)
        update = ingress({"message": query})
        out = {
            **update,
            "message": query,
            **_record_hop(state, "vector_ingress", started, gemini),
        }
        return out

    def cache_gate_node(state: HealthcareVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        case = state["case"]
        update = cache_gate_base(state)
        out = {**update, **_record_hop(state, "cache_gate", started, gemini)}
        case = state.get("case")
        trace_event(
            "cache_gate_result",
            case_id=getattr(case, "case_id", "") if case else "",
            session_id=getattr(case, "session_id", "") if case else "",
            hop="cache_gate",
            cache_hit=update.get("cache_hit"),
            cache_decision=update.get("cache_decision"),
            has_cached_response=bool(update.get("cached_response")),
        )
        return out

    graph.add_node(
        "vector_ingress",
        dict_node_adapter(vector_ingress_node, hop="vector_ingress"),
    )
    graph.add_node("cache_gate", dict_node_adapter(cache_gate_node, hop="cache_gate"))
    for name in agents:
        graph.add_node(name, dict_node_adapter(nodes[name], hop=name))

    graph.add_edge(START, "vector_ingress")
    graph.add_edge("vector_ingress", "cache_gate")
    cache_routes = {name: name for name in agents}
    graph.add_conditional_edges(
        "cache_gate",
        lambda state, _agents=agents: route_after_cache_hc2(state, agents=_agents),
        cache_routes,
    )
    for i in range(len(agents) - 1):
        graph.add_edge(agents[i], agents[i + 1])
    graph.add_edge(agents[-1], END)
    return graph.compile(), gemini, runtime


class HC2Runner:
    """ChorusGraph healthcare multi-agent — cache gate + envelope handoffs (mirror F)."""

    _shared_runtime: FinanceRuntime | None = None

    def __init__(self) -> None:
        self._graphs: Dict[str, Any] = {}
        self._geminis: Dict[str, InstrumentedGeminiClient] = {}
        if HC2Runner._shared_runtime is None:
            HC2Runner._shared_runtime = make_healthcare_envelope_runtime()
        self._shared_runtime = HC2Runner._shared_runtime

    def _runtime(self, case: HealthcareCase) -> tuple[FinanceRuntime, InstrumentedGeminiClient]:
        if case.session_id not in self._geminis:
            self._geminis[case.session_id] = InstrumentedGeminiClient()
        return self._shared_runtime, self._geminis[case.session_id]

    def _session_graph(self, case: HealthcareCase):
        # Graph varies by depth only; semantic cache is global (shared runtime) like B/F.
        key = f"d{case.pipeline_depth}"
        if key not in self._graphs:
            runtime, gemini = self._runtime(case)
            compiled, _, _ = build_healthcare_graph_hc2(
                depth=case.pipeline_depth,
                runtime=runtime,
                gemini=gemini,
            )
            self._graphs[key] = compiled
        runtime, gemini = self._runtime(case)
        return self._graphs[key], runtime, gemini

    def run(self, case: HealthcareCase) -> MultiAgentMeasurement:
        compiled, runtime, gemini = self._session_graph(case)
        started = time.perf_counter()
        gemini.reset_usage()
        trace_event(
            "case_start",
            case_id=case.case_id,
            session_id=case.session_id,
            variant=case.variant,
            depth=case.pipeline_depth,
            message=case.presentation[:120],
        )
        try:
            result = compiled.invoke(
                {
                    "case": case,
                    "hop_metrics": [],
                    "tool_calls": 0,
                    "vector_hops": [],
                    "hop_artifacts": {},
                    "prism_sequence": [],
                    "cache_seed_phrases": cache_seed_phrases(case),
                }
            )
            latency = int((time.perf_counter() - started) * 1000)
            hop_metrics = list(result.get("hop_metrics") or [])
            llm_calls, tokens_in, tokens_out = totals_from_hops(hop_metrics)
            cost_usd = (tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000
            abstained = bool(result.get("abstained"))
            answer = result.get("response") or ""
            embed_count = len(result.get("prism_sequence") or [])
            success = score_healthcare_answer(
                answer=answer,
                must_cite=case.must_cite,
                expected_abstain=case.expected_abstain,
                abstained=abstained,
            )
            trace_event(
                "case_end",
                case_id=case.case_id,
                session_id=case.session_id,
                variant=case.variant,
                depth=case.pipeline_depth,
                latency_ms=latency,
                cache_hit=result.get("cache_hit"),
                llm_calls=llm_calls,
                tokens_in=tokens_in,
                task_success=success,
                hops=hop_names(hop_metrics),
                embed_count=embed_count,
            )
            return MultiAgentMeasurement(
                case_id=case.case_id,
                container="HC2",
                pipeline_depth=case.pipeline_depth,
                message=case.presentation,
                latency_ms=latency,
                llm_calls=llm_calls,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                task_success=success,
                abstained=abstained,
                answer=answer[:2000],
                tool_calls=int(result.get("tool_calls") or 0),
                hop_metrics=hop_metrics,
                embed_count=embed_count,
                cache_hit=result.get("cache_hit"),
                cache_score=result.get("cache_score"),
                variant=case.variant,
            )
        except Exception as exc:
            latency = int((time.perf_counter() - started) * 1000)
            return MultiAgentMeasurement(
                case_id=case.case_id,
                container="HC2",
                pipeline_depth=case.pipeline_depth,
                message=case.presentation,
                latency_ms=latency,
                llm_calls=gemini.usage.llm_calls,
                tokens_in=gemini.usage.tokens_in,
                tokens_out=gemini.usage.tokens_out,
                cost_usd=gemini.usage.cost_usd,
                task_success=False,
                abstained=False,
                answer="",
                error=str(exc),
                variant=case.variant,
            )


__all__ = [
    "HC2Runner",
    "HealthcareVectorState",
    "build_healthcare_graph_hc2",
    "clear_trace",
    "trace_path",
]
