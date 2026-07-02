"""Container C — LangGraph multi-agent healthcare baseline (text/JSON state)."""

from __future__ import annotations

import operator
import time
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from benchmark.healthcare.abstain import (
    retrieve_artifact_from_docs,
    safety_verdict_from_text,
    should_abstain,
)
from benchmark.healthcare.prompts import (
    ANALYZE_SYSTEM,
    DRUG_SYSTEM,
    INTAKE_SYSTEM,
    RETRIEVE_SYSTEM,
    SAFETY_SYSTEM,
    WRITER_SYSTEM,
)
from benchmark.healthcare.tools import check_drug_interactions, retrieve_guidelines
from benchmark.healthcare_workload import PIPELINE_AGENTS, HealthcareCase
from benchmark.multiagent_measure import (
    HopMetric,
    MultiAgentMeasurement,
    score_healthcare_answer,
    totals_from_hops,
)
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient


class HealthcareState(TypedDict, total=False):
    case: HealthcareCase
    drugs: List[str]
    topic: str
    intake_summary: str
    retrieved: List[Dict[str, Any]]
    analysis: str
    interactions: List[Dict[str, Any]]
    safety_verdict: str
    abstained: bool
    response: str
    hop_metrics: Annotated[List[HopMetric], operator.add]
    tool_calls: int
    error: Optional[str]
    hop_artifacts: Dict[str, Dict[str, Any]]
    last_artifact: Dict[str, Any]
    latest_envelope_id: Optional[str]


def _record_hop(
    state: HealthcareState,
    name: str,
    started: float,
    gemini: InstrumentedGeminiClient,
    *,
    tools: int = 0,
) -> Dict[str, Any]:
    return {
        "hop_metrics": [
            HopMetric(
                hop=name,
                latency_ms=int((time.perf_counter() - started) * 1000),
                llm_calls=gemini.usage.llm_calls,
                tokens_in=gemini.usage.tokens_in,
                tokens_out=gemini.usage.tokens_out,
                tool_calls=tools,
            )
        ],
        "tool_calls": int(state.get("tool_calls") or 0) + tools,
    }


def _make_nodes(gemini: InstrumentedGeminiClient) -> Dict[str, Any]:
    def intake_node(state: HealthcareState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        case = state["case"]
        summary = gemini.generate(INTAKE_SYSTEM, case.presentation)
        return {
            "intake_summary": summary,
            "drugs": list(case.drugs),
            "topic": case.topic,
            **_record_hop(state, "intake", started, gemini),
        }

    def retrieve_node(state: HealthcareState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        docs = retrieve_guidelines(state.get("topic") or "", state["case"].presentation)
        summary = gemini.generate(
            RETRIEVE_SYSTEM,
            f"Case:\n{state.get('intake_summary')}\n\nRetrieved:\n{docs}",
        )
        return {
            "retrieved": docs,
            "intake_summary": (state.get("intake_summary") or "") + "\n\nRetrieve:\n" + summary,
            **_record_hop(state, "retrieve", started, gemini, tools=1),
        }

    def analyze_node(state: HealthcareState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        analysis = gemini.generate(
            ANALYZE_SYSTEM,
            f"Intake:\n{state.get('intake_summary')}\n\nGuidelines:\n{state.get('retrieved')}",
        )
        return {"analysis": analysis, **_record_hop(state, "analyze", started, gemini)}

    def drug_node(state: HealthcareState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        drugs = list(state.get("drugs") or [])
        interactions = check_drug_interactions(drugs) if drugs else []
        summary = gemini.generate(DRUG_SYSTEM, f"Tool output:\n{interactions}")
        return {
            "interactions": interactions,
            "analysis": (state.get("analysis") or "") + "\n\nDrug:\n" + summary,
            **_record_hop(state, "drug_check", started, gemini, tools=1 if drugs else 0),
        }

    def safety_node(state: HealthcareState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        verdict = gemini.generate(
            SAFETY_SYSTEM,
            f"Case:\n{state['case'].presentation}\n\nAnalysis:\n{state.get('analysis')}",
        )
        retrieved = list(state.get("retrieved") or [])
        abstained = should_abstain(
            case_topic=str(state.get("topic") or state["case"].topic or ""),
            retrieve_artifact=retrieve_artifact_from_docs(retrieved),
            retrieved_docs=retrieved,
            safety_verdict=safety_verdict_from_text(verdict),
        )
        return {
            "safety_verdict": verdict,
            "abstained": abstained,
            **_record_hop(state, "safety", started, gemini),
        }

    def writer_node(state: HealthcareState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        if state.get("abstained"):
            response = "ABSTAIN: insufficient grounded evidence for a definitive recommendation."
        else:
            response = gemini.generate(
                WRITER_SYSTEM,
                f"Analysis:\n{state.get('analysis')}\n\nGuidelines:\n{state.get('retrieved')}\n\n"
                f"Interactions:\n{state.get('interactions')}",
            )
        return {"response": response, **_record_hop(state, "writer", started, gemini)}

    return {
        "intake": intake_node,
        "retrieve": retrieve_node,
        "analyze": analyze_node,
        "drug_check": drug_node,
        "safety": safety_node,
        "writer": writer_node,
    }


def build_healthcare_graph_c(*, depth: int, gemini: Optional[InstrumentedGeminiClient] = None):
    gemini = gemini or InstrumentedGeminiClient()
    nodes = _make_nodes(gemini)
    agents = PIPELINE_AGENTS[depth]
    graph = StateGraph(HealthcareState)
    for name in agents:
        graph.add_node(name, nodes[name])
    graph.add_edge(START, agents[0])
    for i in range(len(agents) - 1):
        graph.add_edge(agents[i], agents[i + 1])
    graph.add_edge(agents[-1], END)
    return graph.compile(), gemini


class ContainerCRunner:
    """LangGraph healthcare multi-agent baseline."""

    def __init__(self) -> None:
        self._graphs: Dict[int, Any] = {}
        self._gemini = InstrumentedGeminiClient()

    def _graph(self, depth: int):
        if depth not in self._graphs:
            self._graphs[depth], _ = build_healthcare_graph_c(depth=depth, gemini=self._gemini)
        return self._graphs[depth]

    def run(self, case: HealthcareCase) -> MultiAgentMeasurement:
        compiled = self._graph(case.pipeline_depth)
        started = time.perf_counter()
        self._gemini.reset_usage()
        try:
            result = compiled.invoke({"case": case, "hop_metrics": [], "tool_calls": 0})
            latency = int((time.perf_counter() - started) * 1000)
            hop_metrics = list(result.get("hop_metrics") or [])
            llm_calls, tokens_in, tokens_out = totals_from_hops(hop_metrics)
            cost_usd = (tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000
            abstained = bool(result.get("abstained"))
            answer = result.get("response") or ""
            return MultiAgentMeasurement(
                case_id=case.case_id,
                container="C",
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
            )
        except Exception as exc:
            latency = int((time.perf_counter() - started) * 1000)
            return MultiAgentMeasurement(
                case_id=case.case_id,
                container="C",
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
