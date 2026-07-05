"""E7 load test entrypoint."""

from __future__ import annotations

import argparse
import json

from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import NodeContext
from chorusgraph.core.channels import NodeUpdate
from benchmark.load.harness import run_sweep


def _build_tiny_graph():
    def work(ctx: NodeContext) -> NodeUpdate:
        x = int(ctx.read().get("x") or 0)
        return ctx.publish(artifact={"x": x + 1, "response": str(x + 1)}, category_slug="general")

    g = Graph(graph_id="load-smoke")
    g.add_node("work", work)
    g.add_edge(START, "work")
    g.add_edge("work", END)
    return g.compile()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="ChorusGraph E7 load harness")
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--levels", type=str, default="1,2,4,8")
    args = parser.parse_args(argv)
    compiled = _build_tiny_graph()
    levels = [int(x.strip()) for x in args.levels.split(",") if x.strip()]

    def task():
        compiled.invoke({"x": 0})

    reports = run_sweep(task, concurrencies=levels, requests_per_level=args.requests)
    print(json.dumps([r.to_dict() for r in reports], indent=2))


if __name__ == "__main__":
    main()
