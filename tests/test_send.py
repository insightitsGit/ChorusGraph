"""T3 — Send dynamic fan-out exit tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from chorusgraph.core.constants import END, START
from chorusgraph.core.graph import Graph
from chorusgraph.core.node import NodeContext, native_node
from chorusgraph.core.pending_writes import MidStepAbort
from chorusgraph.core.persistence import json_file_checkpointer
from chorusgraph.core.send import Send


def _compile(g: Graph, **kwargs):
    tmp = tempfile.mkdtemp()
    cp = json_file_checkpointer(str(Path(tmp) / "cp"))
    return g.compile(checkpointer=cp, **kwargs), cp


@native_node
def map_runtime(ctx: NodeContext):
    items = ctx.read().get("items") or ["a", "b", "c"]
    return [Send("worker", {"item": x}) for x in items]


@native_node
def reduce_all(ctx: NodeContext):
    outputs = ctx.read().get("branch_outputs") or []
    items = sorted(o.get("item", "") for o in outputs)
    return ctx.publish(artifact={"results": items, "count": len(items)})


def _map_reduce_graph(*, join="all"):
    g = Graph()
    g.add_node("map", map_runtime)
    g.add_node("worker", _worker())
    g.add_node("reduce", reduce_all, join=join)
    g.add_edge(START, "map")
    g.add_edge("worker", "reduce")
    g.add_edge("reduce", END)
    return g


def _worker():
    @native_node
    def worker(ctx: NodeContext):
        item = ctx.read().get("item", "?")
        bid = ctx.branch_id or "main"
        return ctx.publish(artifact={"item": item, "processed": True, "branch_id": bid})

    return worker


def test_map_reduce_runtime_n():
    compiled, _ = _compile(_map_reduce_graph())
    out = compiled.invoke({"items": ["x", "y"]}, config={"configurable": {"thread_id": "t1"}})
    assert out["count"] == 2
    assert sorted(out["results"]) == ["x", "y"]


def test_send_dedup_five_to_three_executions():
    exec_counts: dict[str, int] = {}

    @native_node
    def counting_worker(ctx: NodeContext):
        key = ctx.read().get("item")
        exec_counts[key] = exec_counts.get(key, 0) + 1
        return ctx.publish(artifact={"item": key, "n": exec_counts[key]})

    g = Graph()
    g.add_node("map", map_runtime)
    g.add_node("worker", counting_worker)
    g.add_node("reduce", reduce_all, join="all")
    g.add_edge(START, "map")
    g.add_edge("worker", "reduce")
    g.add_edge("reduce", END)

    compiled, _ = _compile(g)
    out = compiled.invoke(
        {"items": ["a", "b", "a", "c", "b"]},
        config={"configurable": {"thread_id": "dedup"}},
    )
    assert out["count"] == 5
    assert sorted(out["results"]) == ["a", "a", "b", "b", "c"]
    assert exec_counts == {"a": 1, "b": 1, "c": 1}

    events = compiled.last_tracker.events if compiled.last_tracker else []
    send_events = [e for e in events if e.get("type") == "send_batch"]
    assert send_events
    assert send_events[0]["branches_requested"] == 5
    assert send_events[0]["branches_executed"] == 3


def test_quorum_join_early_straggler_lands():
    g = Graph()
    g.add_node("map", map_runtime)
    g.add_node("worker", _worker())
    g.add_node("reduce", reduce_all, join=("quorum", 2))
    g.add_edge(START, "map")
    g.add_edge("worker", "reduce")
    g.add_edge("reduce", END)

    compiled, _ = _compile(g)
    out = compiled.invoke(
        {"items": ["fast1", "fast2", "fast3"]},
        config={"configurable": {"thread_id": "quorum"}},
    )
    assert out["count"] == 3


def test_branch_crash_resume_only_failed_branch():
    exec_log: list[str] = []
    bad_failures = {"n": 0}

    @native_node
    def flaky_worker(ctx: NodeContext):
        item = ctx.read().get("item")
        bid = ctx.branch_id or ""
        exec_log.append(f"{bid}:{item}")
        if item == "bad" and bad_failures["n"] == 0:
            bad_failures["n"] += 1
            raise MidStepAbort({}, super_step=ctx.super_step, active_nodes={bid})
        return ctx.publish(artifact={"item": item})

    g = Graph()
    g.add_node("map", map_runtime)
    g.add_node("worker", flaky_worker)
    g.add_node("reduce", reduce_all, join="all")
    g.add_edge(START, "map")
    g.add_edge("worker", "reduce")
    g.add_edge("reduce", END)

    compiled, _ = _compile(g)
    tid = "branch-crash"
    cfg = {"configurable": {"thread_id": tid}}

    first = compiled.invoke({"items": ["ok", "bad", "fine"]}, config=cfg)
    assert first.get("__mid_step_abort__") is True

    out = compiled.invoke(None, config=cfg)
    assert out.get("count") == 3

    ok_runs = [e for e in exec_log if e.endswith(":ok")]
    fine_runs = [e for e in exec_log if e.endswith(":fine")]
    bad_runs = [e for e in exec_log if e.endswith(":bad")]
    assert len(ok_runs) == 1
    assert len(fine_runs) == 1
    assert len(bad_runs) == 2


def test_deterministic_branch_ordering():
    ids_a: list[str] = []
    ids_b: list[str] = []

    for store, tid in ((ids_a, "det-a"), (ids_b, "det-b")):

        @native_node
        def id_worker(ctx: NodeContext, _store=store):
            _store.append(ctx.branch_id or "")
            item = ctx.read().get("item")
            return ctx.publish(artifact={"item": item})

        g = Graph()
        g.add_node("map", map_runtime)
        g.add_node("worker", id_worker)
        g.add_node("reduce", reduce_all, join="all")
        g.add_edge(START, "map")
        g.add_edge("worker", "reduce")
        g.add_edge("reduce", END)
        compiled, _ = _compile(g)
        compiled.invoke({"items": ["p", "q", "r"]}, config={"configurable": {"thread_id": tid}})

    assert ids_a == ids_b
    assert ids_a == sorted(ids_a)


def test_max_branches_raises():
    g = _map_reduce_graph()
    compiled, _ = _compile(g)
    compiled.config.max_branches = 2
    with pytest.raises(ValueError, match="max_branches"):
        compiled.invoke({"items": ["a", "b", "c"]}, config={"configurable": {"thread_id": "max"}})


def test_branch_same_key_isolation_and_scalar_collision():
    """T3 — parallel branches: append accumulates; scalar last-by-sorted-branch-id wins."""
    from chorusgraph.core.channels import APPEND_LIST_SCALAR_KEYS, BRANCH_SCALAR_COLLISION_RULE

    assert "hop_metrics" in APPEND_LIST_SCALAR_KEYS
    assert BRANCH_SCALAR_COLLISION_RULE == "last_by_sorted_branch_id"

    branch_reads: dict[str, dict[str, Any]] = {}

    @native_node
    def collision_worker(ctx: NodeContext):
        item = ctx.read().get("item", "?")
        bid = ctx.branch_id or "main"
        base = ctx.state.view()
        branch_reads[bid] = {
            "base_shared_tag": base.get("shared_tag"),
            "item": item,
            "read_item": ctx.read().get("item"),
        }
        return ctx.publish(
            artifact={
                "item": item,
                "shared_tag": item,
                "hop_metrics": [{"branch": bid, "item": item}],
            }
        )

    @native_node
    def collision_reduce(ctx: NodeContext):
        outputs = ctx.read().get("branch_outputs") or []
        tags = [o.get("shared_tag") for o in outputs]
        metrics = ctx.read().get("hop_metrics") or []
        return ctx.publish(
            artifact={
                "tags": sorted(tags),
                "metric_count": len(metrics),
                "shared_tag": ctx.read().get("shared_tag"),
            }
        )

    g = Graph()
    g.add_node("map", map_runtime)
    g.add_node("worker", collision_worker)
    g.add_node("reduce", collision_reduce, join="all")
    g.add_edge(START, "map")
    g.add_edge("worker", "reduce")
    g.add_edge("reduce", END)

    items = ["a", "c", "b"]
    run_tags: list[str] = []

    def _run(tid: str):
        branch_reads.clear()
        compiled, _ = _compile(g)
        out = compiled.invoke({"items": items}, config={"configurable": {"thread_id": tid}})
        run_tags.append(out.get("shared_tag"))
        return out

    out1 = _run("iso-1")
    out2 = _run("iso-2")

    assert out1["tags"] == ["a", "b", "c"]
    assert out1["metric_count"] == 3
    assert out1["shared_tag"] == "b"
    assert out1["shared_tag"] == out2["shared_tag"]

    for bid, snap in branch_reads.items():
        assert snap["base_shared_tag"] is None
        assert snap["read_item"] == snap["item"]
