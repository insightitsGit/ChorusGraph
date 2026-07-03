"""Offline healthcare fan-out benchmark — post T3+T4 measured metrics."""

from __future__ import annotations

import json
import time
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List

from benchmark.healthcare.cases import CASES
from chorusgraph.core.constants import END, START
from chorusgraph.core.graph import Graph
from chorusgraph.core.node import NodeContext, native_node
from chorusgraph.core.send import Send

# Realistic width: unique drug pairs from the healthcare corpus (20+ branches).
_DRUG_SETS = [list(c["drugs"]) for c in CASES if c.get("drugs")]
HEALTHCARE_DRUG_PAIRS: List[List[str]] = []
_seen: set[tuple[str, ...]] = set()
for drugs in _DRUG_SETS:
    if len(drugs) >= 2:
        for pair in combinations(sorted(drugs), 2):
            key = tuple(pair)
            if key not in _seen:
                _seen.add(key)
                HEALTHCARE_DRUG_PAIRS.append(list(pair))
    elif len(drugs) == 1:
        for other_drugs in _DRUG_SETS:
            for other in other_drugs:
                if other != drugs[0]:
                    key = tuple(sorted([drugs[0], other]))
                    if key not in _seen:
                        _seen.add(key)
                        HEALTHCARE_DRUG_PAIRS.append(list(key))
while len(HEALTHCARE_DRUG_PAIRS) < 24:
    HEALTHCARE_DRUG_PAIRS.append(["aspirin", "warfarin"])
HEALTHCARE_DRUG_PAIRS = HEALTHCARE_DRUG_PAIRS[:24]

DEPTH6_PIPELINE = ("intake", "retrieve", "analyze", "drug_check", "safety", "writer")
HOPS_PER_BRANCH = len(DEPTH6_PIPELINE)


def _branch_work(llm_calls: Dict[str, int], *, pair: List[str]) -> Dict[str, Any]:
    """Simulate one depth-6 healthcare branch (six LLM-equivalent hops)."""
    for _hop in DEPTH6_PIPELINE:
        llm_calls["n"] += 1
        time.sleep(0.0005)
    return {"pair": pair, "pipeline": list(DEPTH6_PIPELINE), "ok": True}


@native_node
def pair_map(ctx: NodeContext):
    pairs = ctx.read().get("drug_pairs") or HEALTHCARE_DRUG_PAIRS
    return [Send("depth6_branch", {"pair": p}) for p in pairs]


@native_node
def depth6_branch(ctx: NodeContext):
    pair = list(ctx.branch_payload.get("pair") or ctx.read().get("pair") or [])
    llm_state = ctx.read().get("_llm_counter") or {"n": 0}
    artifact = _branch_work(llm_state, pair=pair)
    return ctx.publish(artifact=artifact)


@native_node
def aggregate(ctx: NodeContext):
    outputs = ctx.read().get("branch_outputs") or []
    return ctx.publish(artifact={"checked": len(outputs)})


def _run_serial_baseline(pairs: List[List[str]]) -> Dict[str, Any]:
    """Pre-Improve-1 style: no Send fan-out — sequential depth-6 branch work."""
    llm_calls = {"n": 0}
    started = time.perf_counter()
    results: List[Dict[str, Any]] = []
    for pair in pairs:
        results.append(_branch_work(llm_calls, pair=pair))
    wall_ms = int((time.perf_counter() - started) * 1000)
    return {
        "mode": "serial_pre_improve1",
        "branches_executed": len(results),
        "llm_calls": llm_calls["n"],
        "wall_ms": wall_ms,
    }


def run_offline_fanout_benchmark(*, out_dir: Path | None = None) -> dict:
    llm_calls = {"n": 0}
    pairs = list(HEALTHCARE_DRUG_PAIRS)

    g = Graph(graph_id="hc_fanout")
    g.add_node("map", pair_map)
    g.add_node("depth6_branch", depth6_branch)
    g.add_node("aggregate", aggregate, join="all")
    g.add_edge(START, "map")
    g.add_edge("depth6_branch", "aggregate")
    g.add_edge("aggregate", END)

    compiled = g.compile()
    started = time.perf_counter()
    out = compiled.invoke(
        {"drug_pairs": pairs, "_llm_counter": llm_calls},
        config={"configurable": {"thread_id": "bench-fanout"}},
    )
    parallel_wall_ms = int((time.perf_counter() - started) * 1000)
    events = compiled.last_tracker.events if compiled.last_tracker else []
    send_events = [e for e in events if e.get("type") == "send_batch"]

    serial = _run_serial_baseline(pairs)
    speedup = round(serial["wall_ms"] / parallel_wall_ms, 2) if parallel_wall_ms > 0 else None
    branches_executed = send_events[0]["branches_executed"] if send_events else len(pairs)
    branch_outputs = out.get("branch_outputs") or []

    metrics = {
        "branches_requested": send_events[0]["branches_requested"] if send_events else len(pairs),
        "branches_executed": branches_executed,
        "healthcare_depth": 6,
        "pipeline_hops": list(DEPTH6_PIPELINE),
        "llm_calls": llm_calls["n"],
        "wall_ms": parallel_wall_ms,
        "parallel_wall_ms": parallel_wall_ms,
        "serial_wall_ms": serial["wall_ms"],
        "serial_llm_calls": serial["llm_calls"],
        "speedup_vs_serial": speedup,
        "checked": out.get("checked") if out.get("checked") is not None else len(branch_outputs),
        "improve1_send_fanout": True,
    }
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "fanout_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(run_offline_fanout_benchmark(), indent=2))
