"""Finance agent LangGraph assembly."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from prismlang import PrismEnvelope

from chorusgraph.examples.finance_agent.nodes import (
    make_cache_gate_handler,
    make_researcher_handler,
    make_tool_handler,
    make_validator_handler,
    make_writer_handler,
    route_after_cache,
    route_after_research,
)
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

TENANT_ID = "finance-tenant"
GRAPH_ID = "finance-agent"


class FinanceState(TypedDict, total=False):
    tenant_id: str
    turn_id: str
    message: str
    conversation_history: List[Dict[str, str]]
    needs_tool: bool
    tool_name: str
    tool_args: Dict[str, Any]
    tool_result: Optional[Dict[str, Any]]
    tool_error: Optional[str]
    tool_calls: List[Dict[str, Any]]
    tool_skipped_reason: Optional[str]
    cache_hit: Optional[bool]
    cache_score: Optional[float]
    cache_decision: Optional[str]
    research_plan: str
    draft_response: str
    response: str
    validation: Dict[str, Any]
    memory_recall: Optional[str]
    memory_confidence: Optional[float]
    memory_freshness: Optional[str]
    memory_cache_hit: Optional[bool]
    memory_vector_64: Optional[List[float]]
    memory_subgraph_hash: Optional[str]
    memory_evidence: Optional[List[Dict[str, Any]]]
    rule_chain: Annotated[List[str], operator.add]
    prism_sequence: Annotated[List[PrismEnvelope], operator.add]


def build_finance_graph(
    runtime: Optional[FinanceRuntime] = None,
    *,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    coarse_threshold: float = 0.82,
    verify_threshold: float = 0.85,
):
    runtime = runtime or FinanceRuntime()
    graph = StateGraph(FinanceState)

    graph.add_node("cache_gate", make_cache_gate_handler(
        runtime, coarse_threshold=coarse_threshold, verify_threshold=verify_threshold,
    ))
    graph.add_node("researcher", make_researcher_handler(runtime))
    graph.add_node("tool", make_tool_handler(runtime))
    graph.add_node("writer", make_writer_handler(runtime))
    graph.add_node("validator", make_validator_handler(runtime))

    graph.add_edge(START, "cache_gate")
    graph.add_conditional_edges(
        "cache_gate",
        route_after_cache,
        {"researcher": "researcher", "writer": "writer"},
    )
    graph.add_conditional_edges(
        "researcher",
        route_after_research,
        {"tool": "tool", "writer": "writer"},
    )
    graph.add_edge("tool", "writer")
    graph.add_edge("writer", "validator")
    graph.add_edge("validator", END)

    return graph.compile(checkpointer=checkpointer), runtime


def turn_input(message: str, *, turn_id: Optional[str] = None) -> Dict[str, Any]:
    """Minimal input for a checkpointed turn — history lives in graph state."""
    payload: Dict[str, Any] = {"message": message}
    if turn_id:
        payload["turn_id"] = turn_id
    return payload


def initial_state(message: str, *, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    return {
        "tenant_id": TENANT_ID,
        "message": message,
        "conversation_history": conversation_history or [],
        "needs_tool": False,
        "tool_calls": [],
        "rule_chain": [],
        "prism_sequence": [],
    }
