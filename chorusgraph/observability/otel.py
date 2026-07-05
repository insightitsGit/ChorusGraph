"""OpenTelemetry export helpers — ledger-consistent spans (E4)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from chorusgraph.compat.otel_exporter import ledger_to_spans
from chorusgraph.ledger.models import RouteLedger


def ledger_to_trace(ledger: RouteLedger) -> Dict[str, Any]:
    """Build a trace document: trace_id == ledger run_id for correlation."""
    spans = ledger_to_spans(ledger)
    for step, span in zip(ledger.steps, spans):
        attrs = span["attributes"]
        if step.grounding_score is not None:
            attrs["chorusgraph.grounding_score"] = step.grounding_score
        if step.error_code:
            attrs["chorusgraph.error_code"] = step.error_code
            attrs["chorusgraph.error_kind"] = step.error_kind or ""
            attrs["chorusgraph.retryable"] = bool(step.retryable)
    return {
        "trace_id": ledger.run_id,
        "tenant_id": ledger.tenant_id,
        "graph_id": ledger.graph_id,
        "span_count": len(spans),
        "spans": spans,
    }


def export_spans_otlp_json(ledger: RouteLedger) -> List[Dict[str, Any]]:
    """OTLP-compatible span list (JSON) for Jaeger/Datadog collectors."""
    trace = ledger_to_trace(ledger)
    out: List[Dict[str, Any]] = []
    for span in trace["spans"]:
        out.append(
            {
                "traceId": trace["trace_id"],
                "name": span["name"],
                "duration_ms": span["duration_ms"],
                "attributes": span["attributes"],
            }
        )
    return out
