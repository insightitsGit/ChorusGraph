"""LangGraph migration shim — run StateGraph definitions on ChorusGraph engine (P7)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional

from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import NodeContext, dict_node_adapter
from chorusgraph.core.channels import NodeUpdate


def _extract_handler(node_obj: Any) -> Callable:
    if callable(node_obj):
        return node_obj
    if hasattr(node_obj, "invoke"):
        return node_obj.invoke
    if hasattr(node_obj, "__call__"):
        return node_obj
    raise TypeError(f"Cannot extract handler from {type(node_obj)}")


class StateGraphAdapter:
    """
    Translate a LangGraph ``StateGraph`` builder into ``chorusgraph.Graph``.

    Usage::

        from chorusgraph.compat.langgraph import compile_state_graph
        compiled = compile_state_graph(lg_graph_builder)
    """

    def __init__(self, state_graph: Any) -> None:
        self._lg = state_graph
        self._graph = Graph()

    def _mirror_nodes(self) -> None:
        nodes = getattr(self._lg, "nodes", {}) or {}
        for name, spec in nodes.items():
            if name in (START, END):
                continue
            fn = _extract_handler(getattr(spec, "runnable", spec))
            self._graph.add_node(name, dict_node_adapter(fn, hop=name))

    def _mirror_edges(self) -> None:
        edges = getattr(self._lg, "edges", set()) or set()
        for edge in edges:
            src, dst = edge[0], edge[1]
            if src == START:
                self._graph.add_edge(START, dst)
            elif dst == END:
                self._graph.add_edge(src, END)
            else:
                self._graph.add_edge(src, dst)

        branches = getattr(self._lg, "branches", {}) or {}
        for src, branch_spec in branches.items():
            if not branch_spec:
                continue
            spec = next(iter(branch_spec.values()), None)
            if spec is None:
                continue
            router = getattr(spec, "path", None) or getattr(spec, "router", None)
            paths = getattr(spec, "ends", None) or getattr(spec, "path_map", None) or {}
            if router and paths:
                self._graph.add_conditional_edges(src, router, dict(paths))

    def compile(self, **kwargs: Any) -> Any:
        self._mirror_nodes()
        self._mirror_edges()
        return self._graph.compile(**kwargs)


def compile_state_graph(state_graph: Any, **kwargs: Any) -> Any:
    """Compile a LangGraph StateGraph on the ChorusGraph engine."""
    return StateGraphAdapter(state_graph).compile(**kwargs)


__all__ = ["StateGraphAdapter", "compile_state_graph"]
