"""T4 — local subgraph exit tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from chorusgraph.core.constants import END, START
from chorusgraph.core.graph import Graph
from chorusgraph.core.node import NodeContext, native_node
from chorusgraph.core.persistence import json_file_checkpointer
from chorusgraph.sections.models import CachePolicy


def _cp():
    tmp = tempfile.mkdtemp()
    return json_file_checkpointer(str(Path(tmp) / "cp"))


@native_node
def parent_prep(ctx: NodeContext):
    return ctx.publish(artifact={"message": "hello", "value": 1})


@native_node
def child_work(ctx: NodeContext):
    msg = ctx.read().get("msg", "")
    return ctx.publish(artifact={"child_result": f"{msg}-done"})


@native_node
def parent_finish(ctx: NodeContext):
    return ctx.publish(artifact={"done": True, "result": ctx.read().get("child_result")})


def test_parent_child_mapping_round_trip():
    child_g = Graph()
    child_g.add_node("work", child_work)
    child_g.add_edge(START, "work")
    child_g.add_edge("work", END)
    child = child_g.compile()

    parent_g = Graph()
    parent_g.add_node("prep", parent_prep)
    parent_g.add_subgraph(
        "child_sg", child, input_map={"message": "msg"}, output_map={"child_result": "child_result"}
    )
    parent_g.add_node("finish", parent_finish)
    parent_g.add_edge(START, "prep")
    parent_g.add_edge("prep", "child_sg")
    parent_g.add_edge("child_sg", "finish")
    parent_g.add_edge("finish", END)

    out = parent_g.compile().invoke({}, config={"configurable": {"thread_id": "sg-1"}})
    assert out.get("child_result") == "hello-done"
    assert out.get("done") is True


def test_interrupt_inside_child_surfaces_to_parent():
    @native_node
    def child_hitl(ctx: NodeContext):
        answer = ctx.interrupt({"question": "approve?"})
        return ctx.publish(artifact={"child_result": str(answer)})

    child_g = Graph()
    child_g.add_node("hitl", child_hitl)
    child_g.add_edge(START, "hitl")
    child_g.add_edge("hitl", END)
    child = child_g.compile(checkpointer=_cp())

    parent_g = Graph()
    parent_g.add_node("prep", parent_prep)
    parent_g.add_subgraph(
        "child_sg", child, input_map={"message": "msg"}, output_map={"child_result": "child_result"}
    )
    parent_g.add_edge(START, "prep")
    parent_g.add_edge("prep", "child_sg")
    parent_g.add_edge("child_sg", END)

    parent = parent_g.compile(checkpointer=_cp())
    cfg = {"configurable": {"thread_id": "parent-int"}}
    first = parent.invoke({}, config=cfg)
    assert first.get("__interrupt__") is True

    resumed = parent.invoke({"__resume__": "yes"}, config=cfg)
    assert resumed.get("child_result") == "yes"


def test_namespaced_child_thread_checkpoint():
    cp = _cp()
    child_g = Graph()
    child_g.add_node("work", child_work)
    child_g.add_edge(START, "work")
    child_g.add_edge("work", END)
    child = child_g.compile(checkpointer=cp)

    parent_g = Graph()
    parent_g.add_subgraph(
        "child_sg", child, input_map={"message": "msg"}, output_map={"child_result": "child_result"}
    )
    parent_g.add_edge(START, "child_sg")
    parent_g.add_edge("child_sg", END)

    parent = parent_g.compile(checkpointer=cp)
    cfg = {"configurable": {"thread_id": "parent-t"}}
    parent.invoke({"message": "x"}, config=cfg)
    child_state = parent.get_state({"configurable": {"thread_id": "parent-t__child_sg"}})
    assert child_state.values.get("child_result") == "x-done"


def test_subgraph_cache_hit_zero_child_llm():
    llm_calls = {"n": 0}

    @native_node
    def child_llm(ctx: NodeContext):
        llm_calls["n"] += 1
        return ctx.publish(artifact={"child_result": "cached-path"})

    child_g = Graph()
    child_g.add_node("llm", child_llm)
    child_g.add_edge(START, "llm")
    child_g.add_edge("llm", END)
    child = child_g.compile()

    parent_g = Graph()
    parent_g.add_subgraph(
        "child_sg",
        child,
        input_map={"message": "msg"},
        output_map={"child_result": "child_result"},
        cache_policy=CachePolicy.EXACT,
    )
    parent_g.add_edge(START, "child_sg")
    parent_g.add_edge("child_sg", END)

    from chorusgraph.cache_gate.backend import seed_cache_entry
    from chorusgraph.cache_gate.sidecar import SidecarStore
    from chorusgraph.core.cache_interceptor import CacheRuntime
    from chorusgraph.policy.embedder_guard import build_guarded_cache

    cache = build_guarded_cache("subgraph-cache")
    sidecar = SidecarStore(":memory:")
    seed_cache_entry(
        cache,
        sidecar,
        query="seed-me",
        value={"child_result": "cached-path", "raw_output": "cached-path"},
        category_slug="general",
        cache_policy="exact",
    )
    runtime = CacheRuntime(cache, sidecar, coarse_threshold=0.88, verify_threshold=0.95)
    parent_g2 = Graph()
    parent_g2.add_subgraph(
        "child_sg",
        child,
        input_map={"message": "msg"},
        output_map={"child_result": "child_result"},
        cache_policy=CachePolicy.EXACT,
    )
    parent_g2.add_edge(START, "child_sg")
    parent_g2.add_edge("child_sg", END)
    compiled = parent_g2.compile(cache_runtime=runtime)
    compiled.invoke({"message": "seed-me"}, config={"configurable": {"thread_id": "cache-sg-2"}})
    assert llm_calls["n"] == 0
