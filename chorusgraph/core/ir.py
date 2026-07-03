"""Graph IR — lowered from the DSL."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Mapping, Optional, Set

from chorusgraph.core.bus import ResonanceBus
from chorusgraph.core.cache_interceptor import NodeCacheSpec
from chorusgraph.core.channels import NodeUpdate
from chorusgraph.core.constants import END
from chorusgraph.core.node import NodeFn

RouterFn = Callable[[Dict], str]
RouteVia = str  # "resonance" | "slug" | "router"


@dataclass(frozen=True)
class ConditionalEdge:
    router: RouterFn
    paths: Mapping[str, str]


@dataclass(frozen=True)
class RouteDecision:
    """Resolved successors plus the routing mechanism that selected them."""

    targets: frozenset[str]
    route_via: Optional[RouteVia] = None


@dataclass
class GraphIR:
    nodes: Dict[str, NodeFn] = field(default_factory=dict)
    edges: Dict[str, str] = field(default_factory=dict)
    fan_out: Dict[str, List[str]] = field(default_factory=dict)
    conditional: Dict[str, ConditionalEdge] = field(default_factory=dict)
    node_categories: Dict[str, str] = field(default_factory=dict)
    node_cache_specs: Dict[str, NodeCacheSpec] = field(default_factory=dict)
    interrupt_before: Set[str] = field(default_factory=set)
    interrupt_after: Set[str] = field(default_factory=set)
    entry: Optional[str] = None

    def successor(self, node: str, view: Dict, update: Optional[NodeUpdate] = None, bus: Optional[ResonanceBus] = None) -> Optional[str]:
        decision = self.route_decision(node, view, update, bus)
        return next(iter(decision.targets), None)

    def successors(
        self,
        node: str,
        view: Dict,
        update: Optional[NodeUpdate] = None,
        bus: Optional[ResonanceBus] = None,
    ) -> Set[str]:
        return set(self.route_decision(node, view, update, bus).targets)

    def route_decision(
        self,
        node: str,
        view: Dict,
        update: Optional[NodeUpdate] = None,
        bus: Optional[ResonanceBus] = None,
    ) -> RouteDecision:
        result: Set[str] = set()
        route_via: Optional[RouteVia] = None

        if node in self.fan_out:
            result.update(self.fan_out[node])

        slug = ""
        if update and update.primary:
            slug = str(update.primary.get("category_slug") or "")

        if node in self.conditional:
            spec = self.conditional[node]
            declared_targets = {t for t in spec.paths.values() if not self.is_terminal(t)}

            if (
                len(declared_targets) > 1
                and update
                and update.primary
                and bus is not None
                and slug
            ):
                subscribers = bus.subscribers_for_slug(slug)
                resonance_hits = sorted(
                    node_id for node_id in subscribers if node_id in declared_targets
                )
                if len(resonance_hits) == 1:
                    result.add(resonance_hits[0])
                    route_via = "resonance"

            if not result and slug and slug in spec.paths:
                target = spec.paths[slug]
                if not self.is_terminal(target):
                    result.add(target)
                    route_via = "slug"

            if not result:
                label = spec.router(view)
                if label not in spec.paths:
                    raise KeyError(
                        f"Router for node {node!r} returned unknown label {label!r}; "
                        f"expected one of {sorted(spec.paths)}"
                    )
                target = spec.paths[label]
                if not self.is_terminal(target):
                    result.add(target)
                    route_via = "router"
        elif node in self.edges:
            target = self.edges[node]
            if not self.is_terminal(target):
                result.add(target)

        return RouteDecision(targets=frozenset(result), route_via=route_via)

    def is_terminal(self, node: Optional[str]) -> bool:
        return node is None or node == END
