"""Container D — ChorusGraph multi-agent healthcare (vector envelope between hops)."""

from __future__ import annotations

import operator
import time
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from prismlang import PrismEnvelope

from benchmark.container_c.runner import HealthcareState, _record_hop
from benchmark.container_d.nodes import make_d_nodes
from benchmark.container_d.runtime import make_healthcare_envelope_runtime
from benchmark.healthcare_workload import PIPELINE_AGENTS, HealthcareCase
from benchmark.multiagent_measure import MultiAgentMeasurement, score_healthcare_answer, totals_from_hops
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from chorusgraph.examples.finance_agent.nodes import make_vector_ingress_handler
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime


class HealthcareVectorState(HealthcareState, total=False):
    message: str
    raw_embedding_384: List[float]
    query_vector_64: List[float]
    prism_sequence: Annotated[List[PrismEnvelope], operator.add]
    vector_hops: Annotated[List[Dict[str, Any]], operator.add]


def build_healthcare_graph_d(
    *,
    depth: int,
    runtime: Optional[FinanceRuntime] = None,
    gemini: Optional[InstrumentedGeminiClient] = None,
):
    runtime = runtime or make_healthcare_envelope_runtime()
    gemini = gemini or InstrumentedGeminiClient()
    nodes = make_d_nodes(gemini, runtime)
    agents = PIPELINE_AGENTS[depth]
    ingress = make_vector_ingress_handler(runtime)

    graph = StateGraph(HealthcareVectorState)

    def vector_ingress_node(state: HealthcareVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        case = state["case"]
        update = ingress({"message": case.presentation})
        gemini.reset_usage()
        return {
            **update,
            "message": case.presentation,
            "vector_hops": [{"hop": "vector_ingress", "dim_64": len(update.get("query_vector_64") or [])}],
            **_record_hop(state, "vector_ingress", started, gemini),
        }

    graph.add_node("vector_ingress", vector_ingress_node)
    for name in agents:
        graph.add_node(name, nodes[name])

    graph.add_edge(START, "vector_ingress")
    graph.add_edge("vector_ingress", agents[0])
    for i in range(len(agents) - 1):
        graph.add_edge(agents[i], agents[i + 1])
    graph.add_edge(agents[-1], END)
    return graph.compile(), gemini, runtime


class ContainerDRunner:
    """ChorusGraph healthcare multi-agent — embed once + Prism envelope per hop."""

    def __init__(self) -> None:
        self._graphs: Dict[int, Any] = {}
        self._gemini = InstrumentedGeminiClient()
        self._runtime = make_healthcare_envelope_runtime()

    def _graph(self, depth: int):
        if depth not in self._graphs:
            self._graphs[depth], _, _ = build_healthcare_graph_d(
                depth=depth, runtime=self._runtime, gemini=self._gemini
            )
        return self._graphs[depth]

    def run(self, case: HealthcareCase) -> MultiAgentMeasurement:
        compiled = self._graph(case.pipeline_depth)
        started = time.perf_counter()
        self._gemini.reset_usage()
        self._runtime.session_tool_cache.clear()
        try:
            result = compiled.invoke(
                {
                    "case": case,
                    "hop_metrics": [],
                    "tool_calls": 0,
                    "vector_hops": [],
                    "hop_artifacts": {},
                }
            )
            latency = int((time.perf_counter() - started) * 1000)
            hop_metrics = list(result.get("hop_metrics") or [])
            llm_calls, tokens_in, tokens_out = totals_from_hops(hop_metrics)
            cost_usd = (tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000
            abstained = bool(result.get("abstained"))
            answer = result.get("response") or ""
            embed_count = len(result.get("prism_sequence") or [])
            return MultiAgentMeasurement(
                case_id=case.case_id,
                container="D",
                pipeline_depth=case.pipeline_depth,
                message=case.presentation,
                latency_ms=latency,
                llm_calls=llm_calls,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                task_success=score_healthcare_answer(
                    answer=answer,
                    must_cite=case.must_cite,
                    expected_abstain=case.expected_abstain,
                    abstained=abstained,
                ),
                abstained=abstained,
                answer=answer[:2000],
                tool_calls=int(result.get("tool_calls") or 0),
                hop_metrics=hop_metrics,
                embed_count=embed_count,
            )
        except Exception as exc:
            latency = int((time.perf_counter() - started) * 1000)
            return MultiAgentMeasurement(
                case_id=case.case_id,
                container="D",
                pipeline_depth=case.pipeline_depth,
                message=case.presentation,
                latency_ms=latency,
                llm_calls=self._gemini.usage.llm_calls,
                tokens_in=self._gemini.usage.tokens_in,
                tokens_out=self._gemini.usage.tokens_out,
                cost_usd=self._gemini.usage.cost_usd,
                task_success=False,
                abstained=False,
                answer="",
                error=str(exc),
            )
