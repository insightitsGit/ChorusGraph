"""E4 observability — structured logs, OTel, metrics, health."""

from chorusgraph.observability.health import health_status, readiness_status, start_health_server
from chorusgraph.observability.logging import configure_structured_logging, set_correlation
from chorusgraph.observability.metrics import RuntimeMetrics, get_metrics
from chorusgraph.observability.otel import export_spans_otlp_json, ledger_to_trace

__all__ = [
    "RuntimeMetrics",
    "configure_structured_logging",
    "export_spans_otlp_json",
    "get_metrics",
    "health_status",
    "ledger_to_trace",
    "readiness_status",
    "set_correlation",
    "start_health_server",
]
