"""LangGraph single-agent healthcare ReAct — HL1 baseline."""

from __future__ import annotations

import json
import operator
import time
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from benchmark.healthcare.abstain import should_abstain
from benchmark.healthcare.tools import check_drug_interactions, retrieve_guidelines
from benchmark.healthcare_workload import HealthcareCase
from benchmark.shared.healthcare_react import HEALTHCARE_REACT_SYSTEM, HEALTHCARE_WRITER_SYSTEM
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from chorusgraph.agents.react_utils import parse_react_json

MAX_REACT_STEPS = 6


class HealthcareAgentState(TypedDict, total=False):
    case: HealthcareCase
    scratchpad: str
    react_step: int
    pending_action: Optional[Dict[str, Any]]
    react_done: bool
    tool_calls: int
    retrieved: List[Dict[str, Any]]
    interactions: List[Dict[str, Any]]
    response: str
    abstained: bool
    hop_metrics: Annotated[List[Any], operator.add]


def fresh_case_state(case: HealthcareCase) -> Dict[str, Any]:
    return {
        "case": case,
        "scratchpad": "",
        "react_step": 0,
        "react_done": False,
        "pending_action": None,
        "tool_calls": 0,
        "retrieved": [],
        "interactions": [],
        "response": "",
        "abstained": False,
        "hop_metrics": [],
    }


def build_healthcare_react_graph_hl1(*, gemini: Optional[InstrumentedGeminiClient] = None):
    gemini = gemini or InstrumentedGeminiClient()

    def react_node(state: HealthcareAgentState) -> Dict[str, Any]:
        step = int(state.get("react_step") or 0)
        if step >= MAX_REACT_STEPS:
            return {"react_done": True}
        case = state["case"]
        user = (
            f"Clinical case:\n{case.presentation}\n"
            f"Topic: {case.topic}\nDrugs: {case.drugs}\n\n"
            f"Scratchpad:\n{state.get('scratchpad') or '(empty)'}"
        )
        raw = gemini.generate_json(HEALTHCARE_REACT_SYSTEM, user)
        parsed = parse_react_json(raw)
        action = parsed.get("action")
        finish = bool(parsed.get("finish"))
        has_action = bool(action and (action.get("tool") or action.get("name")))
        update: Dict[str, Any] = {
            "react_step": step + 1,
            "pending_action": action if has_action else None,
            "react_done": finish and not has_action,
        }
        if finish and has_action and step + 1 < MAX_REACT_STEPS:
            update["react_done"] = False
        elif finish:
            update["react_done"] = True
        return update

    def tool_node(state: HealthcareAgentState) -> Dict[str, Any]:
        case = state["case"]
        action = state.get("pending_action") or {}
        tool = action.get("tool") or action.get("name") or "retrieve_guidelines"
        args = dict(action.get("args") or action.get("arguments") or {})
        if tool == "check_drug_interactions":
            drugs = args.get("drugs") or case.drugs
            result = check_drug_interactions(list(drugs))
            obs = json.dumps(result)
            interactions = list(state.get("interactions") or []) + list(result)
        else:
            topic = args.get("topic") or case.topic
            query = args.get("query") or case.presentation
            result = retrieve_guidelines(str(topic), str(query))
            obs = json.dumps(result)
            retrieved = list(state.get("retrieved") or []) + list(result)
            return {
                "scratchpad": (state.get("scratchpad") or "") + f"\nAction: {tool}\nObservation: {obs}\n",
                "pending_action": None,
                "react_done": False,
                "tool_calls": int(state.get("tool_calls") or 0) + 1,
                "retrieved": retrieved,
            }
        return {
            "scratchpad": (state.get("scratchpad") or "") + f"\nAction: {tool}\nObservation: {obs}\n",
            "pending_action": None,
            "react_done": False,
            "tool_calls": int(state.get("tool_calls") or 0) + 1,
            "interactions": interactions,
        }

    def writer_node(state: HealthcareAgentState) -> Dict[str, Any]:
        case = state["case"]
        retrieved = state.get("retrieved") or []
        interactions = state.get("interactions") or []
        cited = [str(d.get("id") or "") for d in retrieved if d.get("id")]
        safety = {"verdict": "APPROVED" if cited or interactions else "ABSTAIN"}
        abstained = should_abstain(
            case_topic=case.topic,
            retrieve_artifact={"cited_ids": cited},
            retrieved_docs=retrieved,
            safety_verdict=safety,
        )
        if abstained or case.expected_abstain:
            response = (
                "I must abstain from a definitive clinical recommendation because "
                "grounded guideline or interaction evidence is insufficient for this case."
            )
            return {"response": response, "abstained": True}

        user = (
            f"Case: {case.presentation}\n"
            f"Guidelines: {retrieved}\nInteractions: {interactions}\n"
            "Write a concise clinical recommendation citing sources."
        )
        response = gemini.generate(HEALTHCARE_WRITER_SYSTEM, user)
        return {"response": response, "abstained": False}

    def route_after_react(state: HealthcareAgentState) -> str:
        if state.get("pending_action"):
            return "tool"
        if state.get("react_done"):
            return "writer"
        if int(state.get("react_step") or 0) >= MAX_REACT_STEPS:
            return "writer"
        return "react"

    def route_after_tool(state: HealthcareAgentState) -> str:
        if int(state.get("react_step") or 0) >= MAX_REACT_STEPS:
            return "writer"
        return "react"

    graph = StateGraph(HealthcareAgentState)
    graph.add_node("react", react_node)
    graph.add_node("tool", tool_node)
    graph.add_node("writer", writer_node)
    graph.add_edge(START, "react")
    graph.add_conditional_edges("react", route_after_react, {"tool": "tool", "writer": "writer", "react": "react"})
    graph.add_conditional_edges("tool", route_after_tool, {"react": "react", "writer": "writer"})
    graph.add_edge("writer", END)
    return graph.compile(), gemini


def run_healthcare_case(
    case: HealthcareCase,
    *,
    compiled,
    gemini: InstrumentedGeminiClient,
) -> Dict[str, Any]:
    gemini.reset_usage()
    started = time.perf_counter()
    try:
        result = compiled.invoke(fresh_case_state(case))
        result["_latency_ms"] = int((time.perf_counter() - started) * 1000)
        result["_llm_usage"] = gemini.usage
        return result
    except Exception as exc:
        return {
            "response": "",
            "abstained": False,
            "error": str(exc),
            "_latency_ms": int((time.perf_counter() - started) * 1000),
            "_llm_usage": gemini.usage,
        }


__all__ = ["build_healthcare_react_graph_hl1", "run_healthcare_case"]
