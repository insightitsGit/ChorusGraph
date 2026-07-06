"""Ledger → OpenTelemetry span exporter — T8."""

from __future__ import annotations

from typing import Any, Dict, List

from chorusgraph.ledger.models import RouteLedger


def ledger_to_spans(ledger: RouteLedger) -> List[Dict[str, Any]]:
    spans: List[Dict[str, Any]] = []
    for step in ledger.steps:
        attrs = {
            "chorusgraph.node": step.node,
            "chorusgraph.route_via": step.route_via or "",
            "chorusgraph.rule_chain": step.rule_chain or [],
        }
        if step.cache_hit is not None:
            attrs["chorusgraph.cache_hit"] = step.cache_hit
        if step.cache_score is not None:
            attrs["chorusgraph.cache_score"] = step.cache_score
        if step.parent_run_id:
            attrs["chorusgraph.parent_run_id"] = step.parent_run_id
        if step.subgraph_node:
            attrs["chorusgraph.subgraph_node"] = step.subgraph_node
        spans.append(
            {
                "name": f"ledger.step.{step.node}",
                "duration_ms": step.duration_ms,
                "attributes": attrs,
            }
        )
    return spans


__all__ = ["ledger_to_spans"]
