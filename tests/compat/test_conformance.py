"""LangGraph-compat conformance corpus — Improve-1 T8."""

from __future__ import annotations

from chorusgraph.core.constants import END, START
from chorusgraph.core.graph import Graph
from chorusgraph.core.node import NodeContext, native_node
from chorusgraph.core.send import Send
from chorusgraph.func import build_graph, entrypoint, task


def _compile(g: Graph):
    return g.compile()


@native_node
def react_agent(ctx: NodeContext):
    return ctx.publish(artifact={"action": "tool_call", "tool": "search"})


@native_node
def react_tools(ctx: NodeContext):
    return ctx.publish(artifact={"observation": "result"})


def pattern_react():
    g = Graph()
    g.add_node("agent", react_agent)
    g.add_node("tools", react_tools)
    g.add_edge(START, "agent")
    g.add_edge("agent", "tools")
    g.add_edge("tools", END)
    return _compile(g)


@native_node
def supervisor(ctx: NodeContext):
    return ctx.publish(artifact={"route": "worker"})


@native_node
def worker(ctx: NodeContext):
    return ctx.publish(artifact={"done": True})


def pattern_supervisor():
    g = Graph()
    g.add_node("supervisor", supervisor)
    g.add_node("worker", worker)
    g.add_edge(START, "supervisor")
    g.add_edge("supervisor", "worker")
    g.add_edge("worker", END)
    return _compile(g)


@native_node
def map_node(ctx: NodeContext):
    return [Send("branch", {"i": x}) for x in range(2)]


@native_node
def branch(ctx: NodeContext):
    return ctx.publish(artifact={"i": ctx.read().get("i")})


@native_node
def reduce_node(ctx: NodeContext):
    return ctx.publish(artifact={"n": len(ctx.read().get("branch_outputs") or [])})


def pattern_map_reduce_send():
    g = Graph()
    g.add_node("map", map_node)
    g.add_node("branch", branch)
    g.add_node("reduce", reduce_node, join="all")
    g.add_edge(START, "map")
    g.add_edge("branch", "reduce")
    g.add_edge("reduce", END)
    return _compile(g)


@native_node
def parent(ctx: NodeContext):
    return ctx.publish(artifact={"message": "x"})


@native_node
def child_node(ctx: NodeContext):
    return ctx.publish(artifact={"child_result": ctx.read().get("msg", "")})


def pattern_subgraph():
    child_g = Graph()
    child_g.add_node("c", child_node)
    child_g.add_edge(START, "c")
    child_g.add_edge("c", END)
    child_compiled = child_g.compile()
    g = Graph()
    g.add_subgraph("sg", child_compiled, input_map={"message": "msg"}, output_map={"child_result": "child_result"})
    g.add_edge(START, "sg")
    g.add_edge("sg", END)
    return _compile(g)


@native_node
def hitl(ctx: NodeContext):
    val = ctx.interrupt({"q": "?"})
    return ctx.publish(artifact={"answer": val})


def pattern_interrupt():
    g = Graph()
    g.add_node("hitl", hitl)
    g.add_edge(START, "hitl")
    g.add_edge("hitl", END)
    return _compile(g)


@task
def t1(v: int) -> int:
    return v + 1


@entrypoint()
def func_entry():
    return 2


def pattern_functional_api():
    return build_graph(func_entry, tasks={}).compile()


PATTERNS = [
    ("react", pattern_react),
    ("supervisor", pattern_supervisor),
    ("map_reduce_send", pattern_map_reduce_send),
    ("subgraph", pattern_subgraph),
    ("interrupt", pattern_interrupt),
    ("functional_api", pattern_functional_api),
    ("react_v2", pattern_react),
    ("supervisor_v2", pattern_supervisor),
    ("send_v2", pattern_map_reduce_send),
    ("subgraph_v2", pattern_subgraph),
]
