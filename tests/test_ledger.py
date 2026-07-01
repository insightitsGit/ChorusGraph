"""Tests for Route Ledger sinks."""

from __future__ import annotations

import os

import pytest

from chorusgraph.ledger import (
    LedgerStep,
    PostgresLedgerSink,
    RouteLedger,
    SqliteLedgerSink,
    get_run,
    list_runs,
)


def test_sqlite_write_and_query_roundtrip(tmp_path):
    db = tmp_path / "ledger.db"
    sink = SqliteLedgerSink(db)
    ledger = RouteLedger(
        tenant_id="acme",
        graph_id="support-agent",
        steps=[
            LedgerStep(node="router", edge_taken="retrieve", rule_chain=["taxonomy=kb"]),
            LedgerStep(node="retrieve", duration_ms=12),
        ],
    )
    sink.write(ledger)

    loaded = get_run(sink, ledger.run_id)
    assert loaded is not None
    assert loaded.tenant_id == "acme"
    assert loaded.graph_id == "support-agent"
    assert len(loaded.steps) == 2
    assert loaded.steps[0].edge_taken == "retrieve"
    assert loaded.steps[0].rule_chain == ["taxonomy=kb"]
    assert loaded.steps[1].duration_ms == 12

    runs = list_runs(sink, graph_id="support-agent", tenant_id="acme")
    assert len(runs) == 1
    assert runs[0].run_id == ledger.run_id


@pytest.mark.skipif(
    not os.environ.get("CHORUSGRAPH_TEST_POSTGRES_DSN"),
    reason="Set CHORUSGRAPH_TEST_POSTGRES_DSN for Postgres smoke test",
)
def test_postgres_smoke():
    sink = PostgresLedgerSink(os.environ["CHORUSGRAPH_TEST_POSTGRES_DSN"])
    ledger = RouteLedger(
        tenant_id="acme",
        graph_id="postgres-smoke",
        steps=[LedgerStep(node="start", duration_ms=1)],
    )
    sink.write(ledger)
    loaded = get_run(sink, ledger.run_id)
    assert loaded is not None
    assert loaded.graph_id == "postgres-smoke"
