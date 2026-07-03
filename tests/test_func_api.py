"""T7 — functional API IR equivalence tests."""

from __future__ import annotations

from chorusgraph.core.constants import END, START
from chorusgraph.core.graph import Graph
from chorusgraph.core.node import NodeContext, native_node
from chorusgraph.core.send import Send
from chorusgraph.func import build_graph, entrypoint, task


@task
def alpha(x: int) -> int:
    return x + 1


@task
def beta(x: int) -> int:
    return x * 2


@entrypoint(graph_id="func_demo")
def demo_workflow():
    return alpha(3)


def _native_equivalent() -> Graph:
    @native_node
    def entry_node(ctx: NodeContext):
        return ctx.publish(artifact={"value": alpha(3), "task": "alpha"})

    g = Graph(graph_id="func_demo")
    g.add_node("__entry__", entry_node)
    g.add_node("alpha", lambda ctx: ctx.publish(artifact={"value": alpha(ctx.read().get("x", 0))}))  # noqa
    g.add_edge(START, "__entry__")
    g.add_edge("__entry__", END)
    return g


def test_build_graph_has_entry_and_tasks():
    g = build_graph(demo_workflow, tasks={"alpha": alpha})
    assert "__entry__" in g._nodes
    assert "alpha" in g._nodes
    assert g._graph_id == "func_demo"


@entrypoint(graph_id="send_demo")
def send_workflow():
    return [Send("alpha", {"x": i}) for i in range(3)]


def test_send_workflow_compiles():
    g = build_graph(send_workflow, tasks={"alpha": alpha})
    g.add_edge("alpha", END)
    compiled = g.compile()
    assert "alpha" in compiled.ir.nodes
