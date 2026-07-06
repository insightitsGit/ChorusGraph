"""Finance agent — native ChorusGraph linear pipeline (researcher → tool → writer)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import dict_node_adapter
from chorusgraph.core.persistence import EngineCheckpointer

from chorusgraph.examples.finance_agent.nodes import (
    make_cache_gate_handler,
    make_researcher_handler,
    make_tool_handler,
    make_validator_handler,
    make_vector_ingress_handler,
    make_writer_handler,
    route_after_cache,
    route_after_research,
)
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

TENANT_ID = "finance-tenant"
GRAPH_ID = "finance-agent"


def build_finance_graph(
    runtime: Optional[FinanceRuntime] = None,
    *,
    checkpointer: Optional[EngineCheckpointer] = None,
    coarse_threshold: float = 0.82,
    verify_threshold: float = 0.85,
):
    runtime = runtime or FinanceRuntime()
    graph = Graph(tenant_id=TENANT_ID, graph_id=GRAPH_ID)

    graph.add_node(
        "vector_ingress",
        dict_node_adapter(make_vector_ingress_handler(runtime), hop="vector_ingress"),
    )
    graph.add_node(
        "cache_gate",
        dict_node_adapter(
            make_cache_gate_handler(
                runtime,
                coarse_threshold=coarse_threshold,
                verify_threshold=verify_threshold,
            ),
            hop="cache_gate",
        ),
    )
    graph.add_node(
        "researcher",
        dict_node_adapter(make_researcher_handler(runtime), hop="researcher"),
    )
    graph.add_node("tool", dict_node_adapter(make_tool_handler(runtime), hop="tool"))
    graph.add_node("writer", dict_node_adapter(make_writer_handler(runtime), hop="writer"))
    graph.add_node("validator", dict_node_adapter(make_validator_handler(runtime), hop="validator"))

    graph.add_edge(START, "vector_ingress")
    graph.add_edge("vector_ingress", "cache_gate")
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


def initial_state(
    message: str, *, conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    return {
        "tenant_id": TENANT_ID,
        "message": message,
        "conversation_history": conversation_history or [],
        "needs_tool": False,
        "tool_calls": [],
        "rule_chain": [],
        "prism_sequence": [],
    }
