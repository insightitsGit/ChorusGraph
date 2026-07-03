"""Finance agent graphs for execution patterns — native ChorusGraph engine (FC1)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from prismlang import PrismEnvelope

from chorusgraph.agents.policy import PlanPolicy
from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import dict_node_adapter
from chorusgraph.core.persistence import EngineCheckpointer
from chorusgraph.examples.finance_agent.nodes import (
    make_cache_gate_handler,
    make_compound_tool_handler,
    make_vector_ingress_handler,
    route_after_cache_pattern,
)
from chorusgraph.examples.finance_agent.pattern_nodes import (
    make_pattern_writer_handler,
    make_plan_solve_handler,
    make_react_agent_handler,
    make_reflection_validator_handler,
)
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

TENANT_ID = "finance-tenant"
GRAPH_ID = "finance-agent-patterns"


class PatternState(TypedDict, total=False):
    tenant_id: str
    turn_id: str
    message: str
    raw_embedding_384: Optional[List[float]]
    query_vector_64: Optional[List[float]]
    execution_pattern: str
    conversation_history: List[Dict[str, str]]
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Any]
    tool_result: Optional[Dict[str, Any]]
    cache_hit: Optional[bool]
    cache_score: Optional[float]
    cache_coarse_score: Optional[float]
    cache_verify_score: Optional[float]
    cache_decision: Optional[str]
    canonical_id: Optional[str]
    cache_seed_phrases: List[str]
    draft_response: str
    response: str
    validation: Dict[str, Any]
    agent_trace: List[Dict[str, Any]]
    plan_steps: List[Dict[str, Any]]
    reflection_demo_wrong_figure: bool
    reflection_pass: int
    memory_recall: Optional[str]
    memory_confidence: Optional[float]
    memory_vector_64: Optional[List[float]]
    memory_subgraph_hash: Optional[str]
    memory_evidence: Optional[List[Dict[str, Any]]]
    rule_chain: List[str]
    prism_sequence: List[PrismEnvelope]


def _add_common_nodes(
    graph: Graph,
    runtime: FinanceRuntime,
    *,
    coarse_threshold: float = 0.82,
    verify_threshold: float = 0.85,
) -> None:
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
        "writer",
        dict_node_adapter(make_pattern_writer_handler(runtime), hop="writer"),
    )
    graph.add_edge("vector_ingress", "cache_gate")


def build_react_graph(
    runtime: Optional[FinanceRuntime] = None,
    *,
    checkpointer: Optional[EngineCheckpointer] = None,
    policy: Optional[PlanPolicy] = None,
    coarse_threshold: float = 0.82,
    verify_threshold: float = 0.85,
):
    runtime = runtime or FinanceRuntime()
    graph = Graph(tenant_id=TENANT_ID, graph_id=GRAPH_ID)
    _add_common_nodes(
        graph, runtime, coarse_threshold=coarse_threshold, verify_threshold=verify_threshold,
    )
    graph.add_node(
        "react_agent",
        dict_node_adapter(make_react_agent_handler(runtime, policy=policy), hop="react_agent"),
    )
    graph.add_node(
        "compound_tool",
        dict_node_adapter(make_compound_tool_handler(runtime), hop="compound_tool"),
    )
    graph.add_node(
        "validator",
        dict_node_adapter(
            make_reflection_validator_handler(runtime, policy=PlanPolicy(max_reflection_passes=1)),
            hop="validator",
        ),
    )

    graph.add_edge(START, "vector_ingress")
    graph.add_conditional_edges(
        "cache_gate",
        route_after_cache_pattern,
        {"writer": "writer", "compound_tool": "compound_tool", "react_agent": "react_agent"},
    )
    graph.add_edge("compound_tool", "writer")
    graph.add_edge("react_agent", "writer")
    graph.add_edge("writer", "validator")
    graph.add_edge("validator", END)
    return graph.compile(checkpointer=checkpointer), runtime


def build_reflection_graph(
    runtime: Optional[FinanceRuntime] = None,
    *,
    checkpointer: Optional[EngineCheckpointer] = None,
    policy: Optional[PlanPolicy] = None,
):
    runtime = runtime or FinanceRuntime()
    graph = Graph(tenant_id=TENANT_ID, graph_id=GRAPH_ID)
    _add_common_nodes(graph, runtime)
    graph.add_node(
        "plan_solve",
        dict_node_adapter(make_plan_solve_handler(runtime, policy=PlanPolicy(max_steps=2)), hop="plan_solve"),
    )
    graph.add_node(
        "validator",
        dict_node_adapter(make_reflection_validator_handler(runtime, policy=policy), hop="validator"),
    )

    graph.add_edge(START, "vector_ingress")
    graph.add_edge("cache_gate", "plan_solve")
    graph.add_edge("plan_solve", "writer")
    graph.add_edge("writer", "validator")
    graph.add_edge("validator", END)
    return graph.compile(checkpointer=checkpointer), runtime


def build_plan_solve_graph(
    runtime: Optional[FinanceRuntime] = None,
    *,
    checkpointer: Optional[EngineCheckpointer] = None,
    policy: Optional[PlanPolicy] = None,
):
    runtime = runtime or FinanceRuntime()
    graph = Graph(tenant_id=TENANT_ID, graph_id=GRAPH_ID)
    _add_common_nodes(graph, runtime)
    graph.add_node(
        "plan_solve",
        dict_node_adapter(make_plan_solve_handler(runtime, policy=policy), hop="plan_solve"),
    )
    graph.add_node(
        "validator",
        dict_node_adapter(
            make_reflection_validator_handler(runtime, policy=PlanPolicy(max_reflection_passes=1)),
            hop="validator",
        ),
    )

    graph.add_edge(START, "vector_ingress")
    graph.add_edge("cache_gate", "plan_solve")
    graph.add_edge("plan_solve", "writer")
    graph.add_edge("writer", "validator")
    graph.add_edge("validator", END)
    return graph.compile(checkpointer=checkpointer), runtime


def pattern_initial_state(message: str, **extra: Any) -> Dict[str, Any]:
    return {
        "tenant_id": TENANT_ID,
        "message": message,
        "tool_calls": [],
        "tool_results": [],
        "rule_chain": [],
        "prism_sequence": [],
        **extra,
    }
