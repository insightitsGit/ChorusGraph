"""P1 tests — Prism core engine (Resonance bus + envelope channels)."""

from __future__ import annotations

import pytest

from chorusgraph.core import END, START, Graph
from chorusgraph.core.bus import ResonanceBus, frequency_for_slug
from chorusgraph.core.channels import ChannelState, NodeUpdate, publish_update
from chorusgraph.core.node import NodeContext


def test_resonance_bus_register_and_dominant():
    bus = ResonanceBus()
    bus.register_node("a", category_slug="short_path")
    bus.register_node("b", category_slug="long_path")
    env = publish_update(
        hop="a",
        artifact={"route": "short_path"},
        vector=[0.1] * 64,
        category_slug="short_path",
        rule_chain=["route=short_path"],
        turn_id=0,
    ).primary
    assert env is not None
    bus.publish_envelope("a", env)
    assert bus.dominant_frequency() == frequency_for_slug("short_path")


def test_superstep_linear_graph():
    order: list[str] = []

    def a(ctx: NodeContext) -> NodeUpdate:
        order.append("a")
        return ctx.publish(artifact={"v": 1}, category_slug="general")

    def b(ctx: NodeContext) -> NodeUpdate:
        order.append("b")
        return ctx.publish(artifact={"v": 2}, category_slug="general")

    g = Graph()
    g.add_node("a", a)
    g.add_node("b", b)
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", END)
    out = g.compile().invoke({"seed": True})
    assert order == ["a", "b"]
    assert len(out["prism_sequence"]) == 2


def test_conditional_routing():
    def route(ctx: NodeContext) -> NodeUpdate:
        pick = ctx.read().get("pick", "left")
        return ctx.publish(artifact={"branch": pick, "raw_output": pick}, category_slug=pick)

    def left(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"out": "L"}, category_slug="left")

    def right(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"out": "R"}, category_slug="right")

    g = Graph()
    g.add_node("route", route)
    g.add_node("left", left, category_slug="left")
    g.add_node("right", right, category_slug="right")
    g.add_edge(START, "route")
    g.add_conditional_edges("route", lambda v: v["branch"], {"left": "left", "right": "right"})
    g.add_edge("left", END)
    g.add_edge("right", END)

    assert g.compile().invoke({"pick": "left"})["out"] == "L"
    assert g.compile().invoke({"pick": "right"})["out"] == "R"


def test_cycle_reactivates_node():
    visits = {"n": 0}

    def flip(ctx: NodeContext) -> NodeUpdate:
        visits["n"] += 1
        done = visits["n"] >= 2
        return ctx.publish(
            artifact={"done": done, "raw_output": str(done)}, category_slug="general"
        )

    g = Graph()
    g.add_node("flip", flip)
    g.add_edge(START, "flip")
    g.add_conditional_edges(
        "flip", lambda v: "end" if v.get("done") else "again", {"again": "flip", "end": END}
    )
    g.compile(recursion_limit=10).invoke({})
    assert visits["n"] == 2


def test_recursion_limit_stops_cycle():
    def loop(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"done": False, "raw_output": "x"}, category_slug="general")

    g = Graph()
    g.add_node("loop", loop)
    g.add_edge(START, "loop")
    g.add_conditional_edges("loop", lambda v: "loop", {"loop": "loop"})
    out = g.compile(recursion_limit=3).invoke({})
    assert len(out["prism_sequence"]) == 3


def test_envelope_sequence_append_only():
    state = ChannelState.from_input({"message": "hi"})
    u1 = publish_update(
        hop="a",
        artifact={"x": 1},
        vector=[0.0] * 64,
        category_slug="general",
        rule_chain=["a"],
        turn_id=0,
    )
    u2 = publish_update(
        hop="b",
        artifact={"y": 2},
        vector=[0.1] * 64,
        category_slug="general",
        rule_chain=["b"],
        turn_id=1,
    )
    state.apply(u1)
    state.apply(u2)
    assert len(state.prism_sequence) == 2
    assert state.latest_envelope_id == u2.primary["envelope_id"]


def test_resonance_routing_by_category_slug():
    """Route via Resonance bus subscribers — not slug-key or router fallback."""

    def route(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"via": "resonance"}, category_slug="left")

    def left(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"out": "L"}, category_slug="left")

    def right(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"out": "R"}, category_slug="right")

    g = Graph()
    g.add_node("route", route)
    g.add_node("left", left, category_slug="left")
    g.add_node("right", right, category_slug="right")
    g.add_edge(START, "route")
    g.add_conditional_edges("route", lambda _v: "missing", {"path_a": "left", "path_b": "right"})
    g.add_edge("left", END)
    g.add_edge("right", END)

    compiled = g.compile()
    assert compiled.invoke({})["out"] == "L"
    assert compiled.last_ledger is not None
    route_step = next(s for s in compiled.last_ledger.steps if s.node == "route")
    assert route_step.route_via == "resonance"


def test_ambiguous_resonance_falls_back_to_router():
    """When multiple subscribers share a slug, router-fn must decide (HC1 ReAct pattern)."""

    visits: list[str] = []

    def react(ctx: NodeContext) -> NodeUpdate:
        visits.append("react")
        view = ctx.read()
        if view.get("go_tool"):
            return ctx.publish(artifact={"go_tool": True}, category_slug="general")
        return ctx.publish(artifact={"go_tool": False}, category_slug="general")

    def tool(ctx: NodeContext) -> NodeUpdate:
        visits.append("tool")
        return ctx.publish(artifact={"done": True}, category_slug="general")

    def writer(ctx: NodeContext) -> NodeUpdate:
        visits.append("writer")
        return ctx.publish(artifact={"done": True}, category_slug="general")

    def route_react(view: dict) -> str:
        return "tool" if view.get("go_tool") else "writer"

    g = Graph()
    g.add_node("react", react)
    g.add_node("tool", tool)
    g.add_node("writer", writer)
    g.add_edge(START, "react")
    g.add_conditional_edges(
        "react", route_react, {"tool": "tool", "writer": "writer", "react": "react"}
    )
    g.add_edge("tool", END)
    g.add_edge("writer", END)

    compiled = g.compile()
    compiled.invoke({"go_tool": True})
    assert visits == ["react", "tool"]

    visits.clear()
    compiled.invoke({"go_tool": False})
    assert visits == ["react", "writer"]

    route_step = next(s for s in compiled.last_ledger.steps if s.node == "react")
    assert route_step.route_via == "router"


def test_parallel_fan_out_same_superstep():
    steps: dict[str, int] = {}

    def split(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"split": True}, category_slug="general")

    def worker_a(ctx: NodeContext) -> NodeUpdate:
        steps["a"] = ctx.super_step
        return ctx.publish(artifact={"a": 1}, category_slug="general")

    def worker_b(ctx: NodeContext) -> NodeUpdate:
        steps["b"] = ctx.super_step
        return ctx.publish(artifact={"b": 2}, category_slug="general")

    g = Graph()
    g.add_node("split", split)
    g.add_node("worker_a", worker_a)
    g.add_node("worker_b", worker_b)
    g.add_edge(START, "split")
    g.add_fan_out("split", "worker_a", "worker_b")
    g.add_edge("worker_a", END)
    g.add_edge("worker_b", END)

    out = g.compile().invoke({})
    assert steps["a"] == steps["b"] == 1
    assert len(out["prism_sequence"]) == 3


@pytest.mark.asyncio
async def test_async_parallel_superstep():
    import asyncio
    import time

    order: list[str] = []

    async def slow_a(ctx: NodeContext) -> NodeUpdate:
        await asyncio.sleep(0.05)
        order.append("a")
        return ctx.publish(artifact={"a": 1}, category_slug="general")

    async def slow_b(ctx: NodeContext) -> NodeUpdate:
        await asyncio.sleep(0.05)
        order.append("b")
        return ctx.publish(artifact={"b": 2}, category_slug="general")

    def split(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"go": True}, category_slug="general")

    g = Graph()
    g.add_node("split", split)
    g.add_node("slow_a", slow_a)
    g.add_node("slow_b", slow_b)
    g.add_edge(START, "split")
    g.add_fan_out("split", "slow_a", "slow_b")
    g.add_edge("slow_a", END)
    g.add_edge("slow_b", END)

    started = time.perf_counter()
    await g.compile().ainvoke({})
    elapsed = time.perf_counter() - started
    assert set(order) == {"a", "b"}
    assert elapsed < 0.09


def test_core_has_zero_langgraph_imports():
    import chorusgraph.core.bus as bus_mod
    import chorusgraph.core.channels as channels_mod
    import chorusgraph.core.graph as graph_mod
    import chorusgraph.core.scheduler as sched_mod

    for mod in (bus_mod, channels_mod, graph_mod, sched_mod):
        source = open(mod.__file__, encoding="utf-8").read().lower()
        assert "langgraph" not in source
