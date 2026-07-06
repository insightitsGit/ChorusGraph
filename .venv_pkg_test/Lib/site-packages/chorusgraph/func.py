"""Functional API sugar — Improve-1 T7."""

from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Optional

from chorusgraph.core.constants import END, START
from chorusgraph.core.graph import Graph
from chorusgraph.core.node import NodeContext, NodeFn, native_node
from chorusgraph.core.persistence import EngineCheckpointer
from chorusgraph.core.scheduler import CompiledGraph
from chorusgraph.core.send import Send

_TASKS: Dict[str, Callable[..., Any]] = {}


def entrypoint(*, checkpointer: Optional[EngineCheckpointer] = None, graph_id: str = "func_graph"):
    def decorator(fn: Callable[..., Any]):
        fn._chorusgraph_entry = True  # type: ignore[attr-defined]
        fn._chorusgraph_checkpointer = checkpointer  # type: ignore[attr-defined]
        fn._chorusgraph_id = graph_id  # type: ignore[attr-defined]
        return fn

    return decorator


def task(fn: Callable[..., Any]) -> Callable[..., Any]:
    _TASKS[fn.__name__] = fn
    fn._chorusgraph_task = True  # type: ignore[attr-defined]
    return fn


def build_graph(entry_fn: Callable[..., Any], *, tasks: Optional[Dict[str, Callable[..., Any]]] = None) -> Graph:
    task_map = dict(tasks or _TASKS)
    g = Graph(graph_id=getattr(entry_fn, "_chorusgraph_id", "func_graph"))

    for name, fn in task_map.items():
        if not getattr(fn, "_chorusgraph_task", False):
            continue

        @native_node
        def task_node(ctx: NodeContext, _fn=fn, _name=name):
            payload = ctx.read()
            kwargs = {}
            for param in inspect.signature(_fn).parameters:
                if param in payload:
                    kwargs[param] = payload[param]
            out = _fn(**kwargs) if kwargs else _fn()
            return ctx.publish(artifact={"task": _name, "value": out})

        g.add_node(name, task_node)

    @native_node
    def entry_node(ctx: NodeContext):
        result = entry_fn()
        if isinstance(result, list) and result and all(isinstance(x, Send) for x in result):
            return result
        return ctx.publish(artifact={"result": result})

    g.add_node("__entry__", entry_node)
    g.add_edge(START, "__entry__")

    preview = entry_fn()
    if isinstance(preview, list) and preview and all(isinstance(x, Send) for x in preview):
        for send in preview:
            if send.target in g._nodes:
                g.add_edge("__entry__", send.target)
        if preview:
            last = sorted({s.target for s in preview})[-1]
            if last in g._nodes:
                g.add_edge(last, END)
    else:
        g.add_edge("__entry__", END)
    return g


def compile_entry(entry_fn: Callable[..., Any], **tasks: Callable[..., Any]) -> CompiledGraph:
    g = build_graph(entry_fn, tasks=tasks or None)
    cp = getattr(entry_fn, "_chorusgraph_checkpointer", None)
    return g.compile(checkpointer=cp)


__all__ = ["build_graph", "compile_entry", "entrypoint", "task"]
