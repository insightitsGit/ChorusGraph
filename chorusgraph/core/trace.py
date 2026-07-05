"""Route Tracker — durable per-hop logging (DESIGN Route Ledger MVP)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from chorusgraph.ledger.models import LedgerStep, RouteLedger
from chorusgraph.ledger.sink import LedgerSink, SqliteLedgerSink

logger = logging.getLogger("chorusgraph.route")


def _stringify_rule_chain(chain: Optional[List[Any]]) -> List[str]:
    out: List[str] = []
    for item in chain or []:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            step = item.get("step")
            out.append(str(step) if step else str(item))
        else:
            out.append(str(item))
    return out


@dataclass
class RouteTracker:
    """
    First-class route logging for the Prism engine.

    Records every node hop with rule_chain, timing, cache scores, and bus
    resonance metadata. Persists to a LedgerSink when configured.
    """

    tenant_id: str
    graph_id: str
    sink: Optional[LedgerSink] = None
    run_id: str = field(default_factory=lambda: str(uuid4()))
    turn_id: Optional[str] = None
    parent_run_id: Optional[str] = None
    subgraph_node: Optional[str] = None
    ledger: RouteLedger = field(init=False)
    _events: List[Dict[str, Any]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self.ledger = RouteLedger(
            run_id=self.run_id,
            turn_id=self.turn_id,
            tenant_id=self.tenant_id,
            graph_id=self.graph_id,
        )

    def record_step(
        self,
        *,
        node: str,
        edge_taken: Optional[str] = None,
        rule_chain: Optional[List[str]] = None,
        duration_ms: int = 0,
        cache_hit: Optional[bool] = None,
        cache_score: Optional[float] = None,
        grounding_score: Optional[float] = None,
        bus_frequency: Optional[float] = None,
        dominant_frequency: Optional[float] = None,
        route_via: Optional[str] = None,
        super_step: Optional[int] = None,
        skipped: bool = False,
        parent_run_id: Optional[str] = None,
        subgraph_node: Optional[str] = None,
        error_code: Optional[str] = None,
        error_kind: Optional[str] = None,
        retryable: Optional[bool] = None,
    ) -> LedgerStep:
        chain = _stringify_rule_chain(rule_chain)
        step = LedgerStep(
            node=node,
            edge_taken=edge_taken,
            route_via=route_via,
            rule_chain=chain,
            duration_ms=duration_ms,
            cache_hit=cache_hit,
            cache_score=cache_score,
            grounding_score=grounding_score,
            parent_run_id=parent_run_id or self.parent_run_id,
            subgraph_node=subgraph_node or self.subgraph_node,
            error_code=error_code,
            error_kind=error_kind,
            retryable=retryable,
        )
        self.ledger.add_step(step)

        event = {
            "type": "route_step",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "tenant_id": self.tenant_id,
            "node": node,
            "edge_taken": edge_taken,
            "route_via": route_via,
            "rule_chain": chain,
            "duration_ms": duration_ms,
            "cache_hit": cache_hit,
            "cache_score": cache_score,
            "grounding_score": grounding_score,
            "bus_frequency": bus_frequency,
            "dominant_frequency": dominant_frequency,
            "super_step": super_step,
            "skipped": skipped,
            "error_code": error_code,
            "error_kind": error_kind,
            "retryable": retryable,
        }
        self._events.append(event)
        logger.info(
            "route %s -> %s (%dms) chain=%s cache_hit=%s",
            node,
            edge_taken,
            duration_ms,
            chain,
            cache_hit,
        )
        return step

    def record_super_step(self, super_step: int, active: List[str]) -> None:
        event = {
            "type": "super_step",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "super_step": super_step,
            "active_nodes": active,
        }
        self._events.append(event)
        logger.debug("super_step %d active=%s", super_step, active)

    def record_send_batch(
        self,
        *,
        send_node: str,
        super_step: int,
        branches_requested: int,
        branches_executed: int,
    ) -> None:
        event = {
            "type": "send_batch",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "send_node": send_node,
            "super_step": super_step,
            "branches_requested": branches_requested,
            "branches_executed": branches_executed,
        }
        self._events.append(event)
        logger.info(
            "send %s step=%d requested=%d executed=%d",
            send_node,
            super_step,
            branches_requested,
            branches_executed,
        )

    def record_interrupt(self, *, node: str, super_step: int) -> None:
        event = {
            "type": "interrupt",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "node": node,
            "super_step": super_step,
        }
        self._events.append(event)
        logger.info("interrupt at node=%s super_step=%d", node, super_step)

    def record_checkpoint(self, *, super_step: int, thread_id: str) -> None:
        event = {
            "type": "checkpoint",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "super_step": super_step,
            "thread_id": thread_id,
        }
        self._events.append(event)
        logger.debug("checkpoint super_step=%d thread=%s", super_step, thread_id)

    def flush(self) -> RouteLedger:
        if self.sink is not None:
            self.sink.write(self.ledger)
        return self.ledger

    @property
    def events(self) -> List[Dict[str, Any]]:
        return list(self._events)


def default_tracker(
    *,
    tenant_id: str,
    graph_id: str,
    sink: Optional[LedgerSink] = None,
    turn_id: Optional[str] = None,
) -> RouteTracker:
    return RouteTracker(
        tenant_id=tenant_id,
        graph_id=graph_id,
        sink=sink or SqliteLedgerSink(":memory:"),
        turn_id=turn_id,
    )


__all__ = ["RouteTracker", "default_tracker"]
