"""Minimal LLM-free demo graph with PrismLang + Route Ledger."""

from __future__ import annotations

import json
import operator
import sys
from pathlib import Path
from typing import Annotated, List, TypedDict

from langgraph.graph import END, START, StateGraph
from prismlang import Category, PrismEnvelope, PrismProjector, TaxonomyConfig, prism_node

from chorusgraph import SqliteLedgerSink, get_run, wrap

TENANT_ID = "demo-tenant"
GRAPH_ID = "demo-routing-graph"


class DemoState(TypedDict):
    tenant_id: str
    message: str
    score: int
    route: str
    rule_chain: Annotated[List[str], operator.add]
    prism_sequence: Annotated[List[PrismEnvelope], operator.add]
    response: str


_DEMO_TAXONOMY = TaxonomyConfig(
    categories=[
        Category(slug="greeting", label="Greeting", keywords=["hi", "hey", "hello"]),
        Category(slug="general", label="General", keywords=["world", "test"]),
    ],
    alpha=0.3,
)


def build_demo_graph():
    projector = PrismProjector(taxonomy=_DEMO_TAXONOMY, tenant_id=TENANT_ID, k=64)

    @prism_node("analyze", projector)
    def analyze(state: DemoState) -> dict:
        text = state.get("message") or ""
        return {"raw_output": text, "score": len(text)}

    def route_decision(state: DemoState) -> dict:
        score = int(state.get("score") or 0)
        if score > 5:
            route = "long_path"
            chain = ["score_gt_5", "route=long_path"]
        else:
            route = "short_path"
            chain = ["score_lte_5", "route=short_path"]
        return {"route": route, "rule_chain": chain}

    def short_path(state: DemoState) -> dict:
        return {"response": f"short:{state.get('message', '')}"}

    def long_path(state: DemoState) -> dict:
        return {"response": f"long:{state.get('message', '')}"}

    def pick_route(state: DemoState) -> str:
        return state.get("route") or "short_path"

    graph = StateGraph(DemoState)
    graph.add_node("analyze", analyze)
    graph.add_node("route_decision", route_decision)
    graph.add_node("short_path", short_path)
    graph.add_node("long_path", long_path)

    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "route_decision")
    graph.add_conditional_edges(
        "route_decision",
        pick_route,
        {"short_path": "short_path", "long_path": "long_path"},
    )
    graph.add_edge("short_path", END)
    graph.add_edge("long_path", END)
    return graph.compile()


def run_demo(*, message: str = "hi", db_path: str | None = None) -> dict:
    sink = SqliteLedgerSink(db_path or ":memory:")
    wrapped = wrap(
        build_demo_graph(),
        tenant_id=TENANT_ID,
        graph_id=GRAPH_ID,
        sink=sink,
    )
    result = wrapped.invoke(
        {
            "tenant_id": TENANT_ID,
            "message": message,
            "score": 0,
            "route": "",
            "rule_chain": [],
            "prism_sequence": [],
            "response": "",
        }
    )
    ledger = wrapped.last_ledger
    assert ledger is not None
    persisted = get_run(sink, ledger.run_id)
    return {
        "result": result,
        "ledger": ledger.model_dump(mode="json"),
        "persisted_match": persisted is not None and len(persisted.steps) == len(ledger.steps),
    }


def main() -> None:
    short = run_demo(message="hi")
    long = run_demo(message="hello world!")
    print("=== short path (message='hi') ===")
    print(json.dumps(short, indent=2, default=str))
    print("\n=== long path (message='hello world!') ===")
    print(json.dumps(long, indent=2, default=str))


if __name__ == "__main__":
    main()
