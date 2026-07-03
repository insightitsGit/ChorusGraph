"""Offline healthcare fan-out benchmark — post T3+T4 measured metrics."""

from __future__ import annotations

import json
import time
from pathlib import Path

from chorusgraph.core.constants import END, START
from chorusgraph.core.graph import Graph
from chorusgraph.core.node import NodeContext, native_node
from chorusgraph.core.send import Send


@native_node
def pair_map(ctx: NodeContext):
    pairs = ctx.read().get("drug_pairs") or [["aspirin", "warfarin"], ["metformin", "lisinopril"]]
    return [Send("pair_check", {"pair": p}) for p in pairs]


@native_node
def pair_check(ctx: NodeContext):
    pair = ctx.read().get("pair") or []
    return ctx.publish(artifact={"pair": pair, "ok": True})


@native_node
def aggregate(ctx: NodeContext):
    outputs = ctx.read().get("branch_outputs") or []
    return ctx.publish(artifact={"checked": len(outputs)})


def run_offline_fanout_benchmark(*, out_dir: Path | None = None) -> dict:
    llm_calls = {"n": 0}

    @native_node
    def cached_child(ctx: NodeContext):
        llm_calls["n"] += 1
        return ctx.publish(artifact={"child_result": "depth6"})

    child_g = Graph(graph_id="hc_child")
    child_g.add_node("leaf", cached_child)
    child_g.add_edge(START, "leaf")
    child_g.add_edge("leaf", END)
    child = child_g.compile()

    g = Graph(graph_id="hc_fanout")
    g.add_node("map", pair_map)
    g.add_node("pair_check", pair_check)
    g.add_node("aggregate", aggregate, join="all")
    g.add_subgraph("depth6", child, input_map={"message": "msg"}, output_map={"child_result": "depth6_out"})
    g.add_edge(START, "map")
    g.add_edge("pair_check", "aggregate")
    g.add_edge("aggregate", "depth6")
    g.add_edge("depth6", END)

    compiled = g.compile()
    started = time.perf_counter()
    out = compiled.invoke(
        {"drug_pairs": [["a", "b"], ["c", "d"], ["a", "b"]]},
        config={"configurable": {"thread_id": "bench-fanout"}},
    )
    wall_ms = int((time.perf_counter() - started) * 1000)
    events = compiled.last_tracker.events if compiled.last_tracker else []
    send_events = [e for e in events if e.get("type") == "send_batch"]
    metrics = {
        "branches_requested": send_events[0]["branches_requested"] if send_events else None,
        "branches_executed": send_events[0]["branches_executed"] if send_events else None,
        "llm_calls": llm_calls["n"],
        "wall_ms": wall_ms,
        "checked": out.get("checked"),
    }
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "fanout_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(run_offline_fanout_benchmark(), indent=2))
