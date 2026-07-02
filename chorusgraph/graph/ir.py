"""Internal graph IR lowered from the builder."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, Optional

from chorusgraph.transport.modes import DEFAULT_TRANSPORT, TransportMode

NodeFn = Callable[[Dict[str, Any]], Dict[str, Any]]
RouterFn = Callable[[Dict[str, Any]], str]


@dataclass(frozen=True)
class ConditionalEdge:
    router: RouterFn
    paths: Mapping[str, str]


@dataclass
class GraphIR:
    """Immutable-ish graph intermediate representation."""

    nodes: Dict[str, NodeFn] = field(default_factory=dict)
    edges: Dict[str, str] = field(default_factory=dict)
    conditional: Dict[str, ConditionalEdge] = field(default_factory=dict)
    edge_transport: Dict[str, TransportMode] = field(default_factory=dict)
    entry: Optional[str] = None
    default_transport: TransportMode = DEFAULT_TRANSPORT

    def transport_for(self, from_node: str) -> TransportMode:
        return self.edge_transport.get(from_node, self.default_transport)

    def successor(self, node: str, state: Dict[str, Any]) -> Optional[str]:
        if node in self.conditional:
            spec = self.conditional[node]
            label = spec.router(state)
            if label not in spec.paths:
                raise KeyError(
                    f"Router for node {node!r} returned unknown label {label!r}; "
                    f"expected one of {sorted(spec.paths)}"
                )
            return spec.paths[label]
        return self.edges.get(node)
