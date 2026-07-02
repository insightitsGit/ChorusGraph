"""Native ChorusGraph builder — replaces LangGraph StateGraph for new graphs."""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional, Type, Union

from chorusgraph.graph.ir import ConditionalEdge, GraphIR, NodeFn, RouterFn
from chorusgraph.runtime.constants import END, START
from chorusgraph.runtime.state import DEFAULT_REDUCERS
from chorusgraph.transport.modes import DEFAULT_TRANSPORT, TransportMode

GraphStateSchema = Optional[Type[Any]]
TransportSpec = Union[TransportMode, str]


class Graph:
    """
    Declarative graph builder (DESIGN §5.1 / §10.1).

    Node handlers are plain ``(state) -> partial state`` callables — no LangGraph dependency.
    """

    def __init__(self, state_schema: GraphStateSchema = None) -> None:
        self._state_schema = state_schema
        self._nodes: Dict[str, NodeFn] = {}
        self._edges: Dict[str, str] = {}
        self._conditional: Dict[str, ConditionalEdge] = {}
        self._edge_transport: Dict[str, TransportMode] = {}
        self._default_transport: TransportMode = DEFAULT_TRANSPORT
        self._entry: Optional[str] = None

    @staticmethod
    def _coerce_transport(mode: TransportSpec) -> TransportMode:
        if isinstance(mode, TransportMode):
            return mode
        return TransportMode(str(mode))

    def set_default_transport(self, mode: TransportSpec) -> None:
        self._default_transport = self._coerce_transport(mode)

    def add_node(self, name: str, fn: NodeFn) -> None:
        if name in (START, END):
            raise ValueError(f"Reserved node name: {name}")
        self._nodes[name] = fn

    def add_edge(self, src: str, dst: str, *, transport: TransportSpec = DEFAULT_TRANSPORT) -> None:
        if dst not in self._nodes and dst != END:
            raise KeyError(f"Unknown destination node: {dst}")
        if src not in self._nodes and src != START:
            raise KeyError(f"Unknown source node: {src}")
        if src == START:
            if self._entry is not None:
                raise ValueError("Graph already has a START edge")
            self._entry = dst
            return
        if src in self._conditional:
            raise ValueError(f"Node {src!r} already has conditional edges")
        self._edges[src] = dst
        if src in self._nodes:
            self._edge_transport[src] = self._coerce_transport(transport)

    def add_conditional_edges(
        self,
        src: str,
        router: RouterFn,
        paths: Mapping[str, str],
        *,
        transport: TransportSpec = DEFAULT_TRANSPORT,
    ) -> None:
        if src not in self._nodes:
            raise KeyError(f"Unknown source node: {src}")
        if src in self._edges:
            raise ValueError(f"Node {src!r} already has a static edge")
        for target in paths.values():
            if target not in self._nodes and target != END:
                raise KeyError(f"Unknown destination node: {target}")
        self._conditional[src] = ConditionalEdge(router=router, paths=dict(paths))
        self._edge_transport[src] = self._coerce_transport(transport)

    def compile(
        self,
        *,
        checkpointer: Any = None,
        reducers: Optional[Dict[str, Callable[[Any, Any], Any]]] = None,
        context: Any = None,
    ) -> CompiledGraph:
        if not self._entry:
            raise ValueError("Graph has no START edge")
        from chorusgraph.runtime.compiled import CompiledGraph

        ir = GraphIR(
            nodes=dict(self._nodes),
            edges=dict(self._edges),
            conditional=dict(self._conditional),
            edge_transport=dict(self._edge_transport),
            entry=self._entry,
            default_transport=self._default_transport,
        )
        return CompiledGraph(
            ir,
            checkpointer=checkpointer,
            reducers=reducers or dict(DEFAULT_REDUCERS),
            context=context,
        )


__all__ = ["Graph"]
