"""LangGraph migration shim — run StateGraph definitions on ChorusGraph engine (P7)."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Union

from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import NodeContext, dict_node_adapter, native_node
from chorusgraph.core.send import Send


def _extract_handler(node_obj: Any) -> Callable:
    if callable(node_obj):
        return node_obj
    if hasattr(node_obj, "func") and callable(node_obj.func):
        return node_obj.func
    if hasattr(node_obj, "invoke"):
        return node_obj.invoke
    if hasattr(node_obj, "__call__"):
        return node_obj
    raise TypeError(f"Cannot extract handler from {type(node_obj)}")


def _is_send_like(obj: Any) -> bool:
    if isinstance(obj, Send):
        return True
    cls = type(obj).__name__
    return cls == "Send" and hasattr(obj, "node") and hasattr(obj, "arg")


def _to_chorus_send(obj: Any) -> Send:
    if isinstance(obj, Send):
        return obj
    target = getattr(obj, "node", None) or getattr(obj, "target", None)
    payload = getattr(obj, "arg", None) or getattr(obj, "payload", None) or {}
    return Send(str(target), dict(payload))


def _coerce_send_list(raw: Any) -> Optional[List[Send]]:
    if raw is None:
        return None
    if isinstance(raw, Send) or _is_send_like(raw):
        return [_to_chorus_send(raw)]
    if isinstance(raw, list) and raw and all(_is_send_like(x) for x in raw):
        return [_to_chorus_send(x) for x in raw]
    return None


class StateGraphAdapter:
    """
    Translate a LangGraph ``StateGraph`` builder into ``chorusgraph.Graph``.

    When a conditional-edge router returns LangGraph ``Send`` objects, a splitter
    node is synthesized so fan-out uses our native ``Send`` API.
    """

    def __init__(self, state_graph: Any) -> None:
        self._lg = state_graph
        self._graph = Graph()
        self._send_splitters: Dict[str, str] = {}
        self._pending_lg_sends: Dict[str, List[Send]] = {}

    @staticmethod
    def _state_key(state: Dict[str, Any]) -> str:
        import json

        return json.dumps({"items": state.get("items"), "i": state.get("i")}, sort_keys=True)

    def _mirror_nodes(self) -> None:
        nodes = getattr(self._lg, "nodes", {}) or {}
        for name, spec in nodes.items():
            if name in (START, END):
                continue
            fn = _extract_handler(getattr(spec, "runnable", spec))
            self._graph.add_node(name, dict_node_adapter(fn, hop=name))

    def _add_send_splitter(self, src: str, router: Callable) -> str:
        splitter = self._send_splitters.get(src)
        if splitter:
            return splitter
        splitter = f"__lg_send_split__{src}"

        @native_node
        def split(ctx: NodeContext):
            key = StateGraphAdapter._state_key(ctx.read())
            sends = self._pending_lg_sends.pop(key, None)
            if sends is None:
                raw = router(ctx.read())
                sends = _coerce_send_list(raw)
            if sends is not None:
                return sends
            raise TypeError(f"Send splitter for {src!r} expected Send list, got cached miss")

        self._graph.add_node(splitter, split)
        self._send_splitters[src] = splitter
        return splitter

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
            if not router:
                continue
            router_fn = _extract_handler(router)
            splitter = self._add_send_splitter(src, router_fn)

            def _dispatch(state: Dict[str, Any], _router: Callable = router_fn) -> str:
                raw = _router(state)
                sends = _coerce_send_list(raw)
                if sends is not None:
                    self._pending_lg_sends[self._state_key(state)] = sends
                    return "__lg_send__"
                return str(raw)

            path_map = {str(k): str(v) for k, v in dict(paths).items()}
            path_map["__lg_send__"] = splitter
            self._graph.add_conditional_edges(src, _dispatch, path_map)

    def compile(self, **kwargs: Any) -> Any:
        self._mirror_nodes()
        self._mirror_edges()
        if self._send_splitters:
            edges = getattr(self._lg, "edges", set()) or set()
            branch_targets: set[str] = set()
            branches = getattr(self._lg, "branches", {}) or {}
            for branch_spec in branches.values():
                for branch in branch_spec.values():
                    ends = getattr(branch, "ends", None)
                    if isinstance(ends, (list, tuple, set)):
                        branch_targets.update(str(x) for x in ends)
                    path_map = getattr(branch, "path_map", None) or {}
                    branch_targets.update(str(v) for v in path_map.values())
            for src, dst in edges:
                if str(src) in branch_targets and str(dst) not in (START, END):
                    self._graph._join_policies[str(dst)] = "all"
        return self._graph.compile(**kwargs)


def compile_state_graph(state_graph: Any, **kwargs: Any) -> Any:
    """Compile a LangGraph StateGraph on the ChorusGraph engine."""
    return StateGraphAdapter(state_graph).compile(**kwargs)


__all__ = ["StateGraphAdapter", "compile_state_graph"]
