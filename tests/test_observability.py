"""E4 observability tests."""

from __future__ import annotations

import json
import urllib.request

from chorusgraph.ledger.models import LedgerStep, RouteLedger
from chorusgraph.observability import (
    export_spans_otlp_json,
    get_metrics,
    health_status,
    ledger_to_trace,
    readiness_status,
    set_correlation,
    start_health_server,
)


def test_ledger_trace_id_matches_run_id():
    ledger = RouteLedger(tenant_id="t1", graph_id="g1", run_id="run-abc")
    ledger.add_step(LedgerStep(node="writer", duration_ms=12, cache_hit=True, cache_score=0.9))
    trace = ledger_to_trace(ledger)
    assert trace["trace_id"] == "run-abc"
    assert trace["span_count"] == 1
    assert trace["spans"][0]["attributes"]["chorusgraph.cache_hit"] is True


def test_otlp_export_includes_error_attrs():
    ledger = RouteLedger(tenant_id="t1", graph_id="g1")
    ledger.add_step(
        LedgerStep(
            node="tool", duration_ms=5, error_code="timeout", error_kind="transient", retryable=True
        )
    )
    spans = export_spans_otlp_json(ledger)
    assert spans[0]["attributes"]["chorusgraph.error_code"] == "timeout"


def test_health_and_readiness():
    assert health_status()["status"] == "ok"
    assert readiness_status(lambda: True)["ready"] is True
    assert readiness_status(lambda: False)["ready"] is False


def test_health_server_endpoints():
    server = start_health_server("127.0.0.1", 0)
    port = server.server_port
    try:
        health = json.loads(
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2).read()
        )
        metrics = json.loads(
            urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=2).read()
        )
        assert health["status"] == "ok"
        assert "llm_calls" in metrics
    finally:
        server.shutdown()


def test_correlation_context():
    set_correlation(correlation_id="corr-1", run_id="run-1")
    from chorusgraph.observability.logging import get_correlation_id, get_run_id

    assert get_correlation_id() == "corr-1"
    assert get_run_id() == "run-1"


def test_metrics_snapshot():
    m = get_metrics()
    m.inc("llm_calls", 2)
    m.inc("cache_hits", 1)
    m.inc("cache_misses", 1)
    snap = m.snapshot()
    assert snap["llm_calls"] >= 2
    assert snap["cache_hit_rate"] > 0
