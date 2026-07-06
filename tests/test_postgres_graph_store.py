"""PostgresGraphStore — skipped unless CHORUSGRAPH_PG_DSN + license file are set."""

from __future__ import annotations

import os
import threading

import pytest

from chorusgraph.licensing import ENTERPRISE_PERSISTENCE
from chorusgraph.persistence.postgres_graph_store import PostgresGraphStore
from tests.support.license_fixture import write_test_license

PG_DSN = os.environ.get("CHORUSGRAPH_PG_DSN")

pytestmark = pytest.mark.skipif(not PG_DSN, reason="CHORUSGRAPH_PG_DSN not configured")


@pytest.fixture
def enterprise_license(tmp_path, monkeypatch):
    path = write_test_license(tmp_path / "lic.json", features=[ENTERPRISE_PERSISTENCE])
    monkeypatch.setenv("CHORUSGRAPH_LICENSE_FILE", str(path))
    return path


def _sample_delta(source_id: str, node_id: str):
    from prismcortex.models import DeltaOp, Node, Operation, Provenance, StateDelta

    node = Node(
        id=node_id,
        label=f"node {node_id}",
        embedding=[0.1] * 128,
        weight=1.0,
        provenance=Provenance(source_id=source_id, agent_id="test-agent"),
    )
    return StateDelta(ops=[DeltaOp(operation=Operation.ASSIMILATE, node=node)])


def test_postgres_graph_store_survives_restart(enterprise_license):
    store_a = PostgresGraphStore(PG_DSN, tenant_id="pg-graph-test")
    store_a.apply(_sample_delta("s1", "n1"))
    assert store_a.node_count() == 1
    store_a.close()

    store_b = PostgresGraphStore(PG_DSN, tenant_id="pg-graph-test")
    assert store_b.node_count() == 1
    store_b.close()


def test_postgres_graph_store_concurrent_writes(enterprise_license):
    errors: list[Exception] = []

    def writer(node_id: str) -> None:
        try:
            store = PostgresGraphStore(PG_DSN, tenant_id="pg-concurrent")
            store.apply(_sample_delta(f"src-{node_id}", node_id))
            store.close()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(f"n{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    final = PostgresGraphStore(PG_DSN, tenant_id="pg-concurrent")
    assert final.node_count() == 4
    final.close()
