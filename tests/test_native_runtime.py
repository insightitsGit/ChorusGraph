"""Tests for the native ChorusGraph runtime (no LangGraph execution)."""

from __future__ import annotations

from chorusgraph.graph.builder import Graph
from chorusgraph.runtime.constants import END, START


def test_native_linear_graph():
    graph = Graph()
    graph.add_node("a", lambda s: {"x": (s.get("x") or 0) + 1})
    graph.add_node("b", lambda s: {"y": s.get("x", 0) * 2})
    graph.add_edge(START, "a")
    graph.add_edge("a", "b")
    graph.add_edge("b", END)

    result = graph.compile().invoke({"x": 0})
    assert result["x"] == 1
    assert result["y"] == 2


def test_native_conditional_graph():
    graph = Graph()
    graph.add_node("route", lambda s: {"branch": "b" if s.get("pick") == "b" else "a"})
    graph.add_node("a", lambda s: {"out": "path_a"})
    graph.add_node("b", lambda s: {"out": "path_b"})
    graph.add_edge(START, "route")
    graph.add_conditional_edges("route", lambda s: s["branch"], {"a": "a", "b": "b"})
    graph.add_edge("a", END)
    graph.add_edge("b", END)

    assert graph.compile().invoke({"pick": "a"})["out"] == "path_a"
    assert graph.compile().invoke({"pick": "b"})["out"] == "path_b"


def test_native_list_merge():
    graph = Graph()
    graph.add_node("first", lambda s: {"items": ["a"]})
    graph.add_node("second", lambda s: {"items": ["b"]})
    graph.add_edge(START, "first")
    graph.add_edge("first", "second")
    graph.add_edge("second", END)

    result = graph.compile().invoke({"items": []})
    assert result["items"] == ["a", "b"]


def test_native_debug_stream_events():
    graph = Graph()
    graph.add_node("only", lambda s: {"done": True})
    graph.add_edge(START, "only")
    graph.add_edge("only", END)

    events = list(graph.compile().stream({}, stream_mode="debug"))
    types = [e["type"] for e in events]
    assert types == ["task", "task_result"]
    assert events[0]["payload"]["name"] == "only"
    assert events[1]["payload"]["result"] == {"done": True}


def test_compiled_graph_has_native_marker():
    graph = Graph()
    graph.add_node("n", lambda s: {})
    graph.add_edge(START, "n")
    graph.add_edge("n", END)
    compiled = graph.compile()
    assert getattr(compiled, "_native", False) is True
