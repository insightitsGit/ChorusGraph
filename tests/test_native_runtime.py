"""Tests for the native ChorusGraph core engine."""

from __future__ import annotations

from chorusgraph.core import END, START, Graph
from chorusgraph.core.channels import NodeUpdate
from chorusgraph.core.node import NodeContext


def test_native_linear_graph():
    def a(ctx: NodeContext) -> NodeUpdate:
        view = ctx.read()
        return ctx.publish(artifact={"x": (view.get("x") or 0) + 1}, category_slug="general")

    def b(ctx: NodeContext) -> NodeUpdate:
        view = ctx.read()
        return ctx.publish(artifact={"y": view.get("x", 0) * 2}, category_slug="general")

    graph = Graph()
    graph.add_node("a", a)
    graph.add_node("b", b)
    graph.add_edge(START, "a")
    graph.add_edge("a", "b")
    graph.add_edge("b", END)

    result = graph.compile().invoke({"x": 0})
    assert result["x"] == 1
    assert result["y"] == 2


def test_native_conditional_graph():
    def route(ctx: NodeContext) -> NodeUpdate:
        view = ctx.read()
        branch = "b" if view.get("pick") == "b" else "a"
        return ctx.publish(artifact={"branch": branch}, category_slug=branch)

    def path_a(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"out": "path_a"}, category_slug="a")

    def path_b(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"out": "path_b"}, category_slug="b")

    graph = Graph()
    graph.add_node("route", route)
    graph.add_node("a", path_a, category_slug="a")
    graph.add_node("b", path_b, category_slug="b")
    graph.add_edge(START, "route")
    graph.add_conditional_edges("route", lambda _v: "missing", {"a": "a", "b": "b"})
    graph.add_edge("a", END)
    graph.add_edge("b", END)

    assert graph.compile().invoke({"pick": "a"})["out"] == "path_a"
    assert graph.compile().invoke({"pick": "b"})["out"] == "path_b"


def test_native_list_merge():
    def first(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"items": ["a"]}, category_slug="general")

    def second(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"items": ["b"]}, category_slug="general")

    graph = Graph()
    graph.add_node("first", first)
    graph.add_node("second", second)
    graph.add_edge(START, "first")
    graph.add_edge("first", "second")
    graph.add_edge("second", END)

    result = graph.compile().invoke({"items": []})
    assert result["items"] == ["a", "b"]


def test_native_debug_stream_events():
    def only(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"done": True}, category_slug="general")

    graph = Graph()
    graph.add_node("only", only)
    graph.add_edge(START, "only")
    graph.add_edge("only", END)

    events = list(graph.compile().stream({}, stream_mode="debug"))
    types = [e["type"] for e in events]
    assert types == ["task", "task_result"]
    assert events[0]["payload"]["name"] == "only"
    assert events[1]["payload"]["result"]["done"] is True


def test_compiled_graph_has_native_marker():
    def n(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={}, category_slug="general")

    graph = Graph()
    graph.add_node("n", n)
    graph.add_edge(START, "n")
    graph.add_edge("n", END)
    compiled = graph.compile()
    assert getattr(compiled, "_native", False) is True
