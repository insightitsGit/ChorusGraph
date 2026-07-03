"""ChorusGraph DSL — public authoring surface (ENGINE §7)."""

from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Mapping, Optional, Type

from prismlang import PrismProjector

from chorusgraph.core.bus import ResonanceBus
from chorusgraph.core.cache_interceptor import CacheInterceptor, CacheRuntime, NodeCacheSpec
from chorusgraph.core.constants import END, START
from chorusgraph.core.ir import ConditionalEdge, GraphIR
from chorusgraph.core.node import NodeContext, NodeFn, dict_node_adapter, is_native_node
from chorusgraph.core.persistence import EngineCheckpointer
from chorusgraph.core.scheduler import CompiledGraph, EngineConfig
from chorusgraph.core.trace import RouteTracker
from chorusgraph.core.transport_router import TransportRouter
from chorusgraph.ledger.sink import LedgerSink
from chorusgraph.nodes.roles import Node
from chorusgraph.sections.models import CachePolicy
from chorusgraph.transport.modes import TransportMode

GraphStateSchema = Optional[Type[Any]]
LegacyNodeFn = Callable[[Dict[str, Any]], Dict[str, Any]]


class Graph:
    """
    Prism-native graph builder.

    Nodes communicate via ``PrismEnvelope`` channels on the Resonance bus —
    not raw dict handoffs.
    """

    def __init__(
        self,
        state_schema: GraphStateSchema = None,
        *,
        tenant_id: str = "default",
        projector: Optional[PrismProjector] = None,
        graph_id: str = "graph",
    ) -> None:
        self._state_schema = state_schema
        self._tenant_id = tenant_id
        self._projector = projector
        self._graph_id = graph_id
        self._nodes: Dict[str, NodeFn] = {}
        self._edges: Dict[str, str] = {}
        self._fan_out: Dict[str, List[str]] = {}
        self._conditional: Dict[str, ConditionalEdge] = {}
        self._node_categories: Dict[str, str] = {}
        self._node_cache: Dict[str, NodeCacheSpec] = {}
        self._interrupt_before: set[str] = set()
        self._interrupt_after: set[str] = set()
        self._entry: Optional[str] = None

    def add_node(
        self,
        name: str,
        fn: NodeFn | LegacyNodeFn,
        *,
        category_slug: str = "general",
        cache_policy: CachePolicy = CachePolicy.NO_CACHE,
        cache_query_key: str = "message",
    ) -> None:
        if name in (START, END):
            raise ValueError(f"Reserved node name: {name}")
        if not callable(fn):
            raise TypeError("Node handler must be callable")
        is_native = is_native_node(fn)
        if is_native:
            wrapped = fn  # type: ignore[assignment]
        else:
            wrapped = dict_node_adapter(fn, hop=name)  # type: ignore[arg-type]
        self._nodes[name] = wrapped
        self._node_categories[name] = category_slug
        if cache_policy != CachePolicy.NO_CACHE:
            self._node_cache[name] = NodeCacheSpec(
                node_id=name,
                category_slug=category_slug,
                cache_policy=cache_policy,
                query_key=cache_query_key,
            )

    def add_role_node(self, name: str, role_node: Node, fn: NodeFn | LegacyNodeFn) -> None:
        slug = role_node.role.role if role_node.role else "general"
        self.add_node(name, fn, category_slug=slug)

    def set_interrupt_before(self, *nodes: str) -> None:
        self._interrupt_before.update(nodes)

    def set_interrupt_after(self, *nodes: str) -> None:
        self._interrupt_after.update(nodes)

    def add_edge(self, src: str, dst: str) -> None:
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
        if src in self._fan_out:
            raise ValueError(f"Node {src!r} already has fan-out edges")
        self._edges[src] = dst

    def add_fan_out(self, src: str, *dsts: str) -> None:
        if src not in self._nodes:
            raise KeyError(f"Unknown source node: {src}")
        if src in self._edges:
            raise ValueError(f"Node {src!r} already has a static edge")
        if src in self._conditional:
            raise ValueError(f"Node {src!r} already has conditional edges")
        if not dsts:
            raise ValueError("add_fan_out requires at least one destination")
        for dst in dsts:
            if dst not in self._nodes and dst != END:
                raise KeyError(f"Unknown destination node: {dst}")
        self._fan_out[src] = list(dsts)

    def add_conditional_edges(
        self,
        src: str,
        router: Callable[[Dict[str, Any]], str],
        paths: Mapping[str, str],
    ) -> None:
        if src not in self._nodes:
            raise KeyError(f"Unknown source node: {src}")
        if src in self._edges:
            raise ValueError(f"Node {src!r} already has a static edge")
        for target in paths.values():
            if target not in self._nodes and target != END:
                raise KeyError(f"Unknown destination node: {target}")
        self._conditional[src] = ConditionalEdge(router=router, paths=dict(paths))

    def set_entry(self, node: str) -> None:
        if node not in self._nodes:
            raise KeyError(f"Unknown entry node: {node}")
        self._entry = node

    def compile(
        self,
        *,
        recursion_limit: int = 25,
        checkpointer: Optional[EngineCheckpointer] = None,
        ledger_sink: Optional[LedgerSink] = None,
        cache_runtime: Optional[CacheRuntime] = None,
        transport: Optional[TransportRouter] = None,
    ) -> CompiledGraph:
        if not self._entry:
            raise ValueError("Graph has no START edge — use add_edge(START, first_node)")

        bus = ResonanceBus()
        for node_id, slug in self._node_categories.items():
            bus.register_node(node_id, category_slug=slug)

        cache_interceptor = None
        if cache_runtime is not None and self._node_cache:
            cache_interceptor = CacheInterceptor(cache_runtime, dict(self._node_cache))

        ir = GraphIR(
            nodes=dict(self._nodes),
            edges=dict(self._edges),
            fan_out=dict(self._fan_out),
            conditional=dict(self._conditional),
            node_categories=dict(self._node_categories),
            node_cache_specs=dict(self._node_cache),
            interrupt_before=set(self._interrupt_before),
            interrupt_after=set(self._interrupt_after),
            entry=self._entry,
        )
        return CompiledGraph(
            ir=ir,
            bus=bus,
            projector=self._projector,
            config=EngineConfig(
                recursion_limit=recursion_limit,
                graph_id=self._graph_id,
                tenant_id=self._tenant_id,
            ),
            checkpointer=checkpointer,
            ledger_sink=ledger_sink,
            cache_interceptor=cache_interceptor,
            transport=transport or TransportRouter(tenant_id=self._tenant_id),
        )


__all__ = ["END", "Graph", "START"]
