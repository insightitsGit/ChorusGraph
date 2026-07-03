"""Minimal LLM-free demo graph — Prism core engine (Resonance bus + envelopes)."""

from __future__ import annotations

import json

from prismlang import Category, PrismProjector, TaxonomyConfig

from chorusgraph import SqliteLedgerSink, get_run, wrap
from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import NodeContext
from chorusgraph.core.channels import NodeUpdate

TENANT_ID = "demo-tenant"
GRAPH_ID = "demo-routing-graph"

_DEMO_TAXONOMY = TaxonomyConfig(
    categories=[
        Category(slug="greeting", label="Greeting", keywords=["hi", "hey", "hello"]),
        Category(slug="general", label="General", keywords=["world", "test"]),
    ],
    alpha=0.3,
)


def build_demo_graph():
    projector = PrismProjector(taxonomy=_DEMO_TAXONOMY, tenant_id=TENANT_ID, k=64)

    def analyze(ctx: NodeContext) -> NodeUpdate:
        text = ctx.read().get("message") or ""
        return ctx.publish(
            artifact={"raw_output": text, "score": len(text)},
            category_slug="general",
        )

    def route_decision(ctx: NodeContext) -> NodeUpdate:
        score = int(ctx.read().get("score") or 0)
        if score > 5:
            route = "long_path"
            chain = ["score_gt_5", "route=long_path"]
        else:
            route = "short_path"
            chain = ["score_lte_5", "route=short_path"]
        return ctx.publish(
            artifact={"route": route, "raw_output": route},
            category_slug=route,
            rule_chain=chain,
        )

    def short_path(ctx: NodeContext) -> NodeUpdate:
        msg = ctx.read().get("message") or ""
        return ctx.publish(
            artifact={"response": f"short:{msg}", "raw_output": f"short:{msg}"},
            category_slug="short_path",
        )

    def long_path(ctx: NodeContext) -> NodeUpdate:
        msg = ctx.read().get("message") or ""
        return ctx.publish(
            artifact={"response": f"long:{msg}", "raw_output": f"long:{msg}"},
            category_slug="long_path",
        )

    def pick_route(view: dict) -> str:
        return view.get("route") or "short_path"

    graph = Graph(
        tenant_id=TENANT_ID,
        projector=projector,
        graph_id=GRAPH_ID,
    )
    graph.add_node("analyze", analyze, category_slug="general")
    graph.add_node("route_decision", route_decision, category_slug="general")
    graph.add_node("short_path", short_path, category_slug="short_path")
    graph.add_node("long_path", long_path, category_slug="long_path")

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
    compiled = build_demo_graph()
    wrapped = wrap(
        compiled,
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
