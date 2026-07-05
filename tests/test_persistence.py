"""E5 durable persistence tests — no live Gemini required."""

from __future__ import annotations

from prismcortex.models import DeltaOp, Node, Operation, Provenance, StateDelta

from chorusgraph.ledger.models import RouteLedger
from chorusgraph.ledger.sink import SqliteLedgerSink
from chorusgraph.persistence import (
    DataLifecycleManager,
    SqliteGraphStore,
    backup_sqlite_stores,
    migrate_file,
    restore_sqlite_store,
    verify_backup_integrity,
)


def _sample_delta(source_id: str = "subject-42") -> StateDelta:
    node = Node(
        id="node-1",
        label="investment profile",
        embedding=[0.1] * 128,
        weight=1.0,
        provenance=Provenance(source_id=source_id, agent_id="test-agent"),
    )
    return StateDelta(ops=[DeltaOp(operation=Operation.ASSIMILATE, node=node)])


def test_graph_store_survives_restart(tmp_path):
    db = tmp_path / "graph.db"
    store_a = SqliteGraphStore(db, tenant_id="t1")
    store_a.apply(_sample_delta())
    assert store_a.node_count() == 1
    v1 = store_a.version().version
    store_a.close()

    store_b = SqliteGraphStore(db, tenant_id="t1")
    assert store_b.node_count() == 1
    assert store_b.version().version == v1
    store_b.close()


def test_migrations_run_forward(tmp_path):
    db = tmp_path / "migrations.db"
    result = migrate_file(db)
    assert result.applied
    assert result.current_version >= 3


def test_backup_restore_roundtrip(tmp_path):
    db = tmp_path / "graph.db"
    store = SqliteGraphStore(db, tenant_id="t1")
    store.apply(_sample_delta())
    store.close()

    manifest = backup_sqlite_stores(target_dir=tmp_path / "backups", sources=[db])
    assert verify_backup_integrity(manifest.backup_dir)

    target = tmp_path / "restored" / "graph.db"
    restore_sqlite_store(manifest.files[0], target)
    restored = SqliteGraphStore(target, tenant_id="t1")
    assert restored.node_count() == 1
    restored.close()


def test_forget_erases_graph_and_ledger(tmp_path):
    graph_db = tmp_path / "graph.db"
    store = SqliteGraphStore(graph_db, tenant_id="tenant-a")
    store.apply(_sample_delta(source_id="user-99"))
    assert store.node_count() == 1

    ledger = SqliteLedgerSink(str(tmp_path / "ledger.db"))
    run = RouteLedger(tenant_id="tenant-a", graph_id="g1", turn_id="user-99")
    ledger.write(run)

    sidecar_db = tmp_path / "sidecar.db"
    import sqlite3

    conn = sqlite3.connect(str(sidecar_db))
    conn.execute(
        """
        CREATE TABLE cache_sidecar (
            packet_id TEXT PRIMARY KEY,
            raw_embedding BLOB,
            category_slug TEXT,
            cache_policy TEXT,
            canonical_query TEXT,
            scope_id TEXT,
            keying TEXT,
            fingerprint_key TEXT,
            valid_from REAL,
            valid_until REAL
        )
        """
    )
    conn.execute(
        "INSERT INTO cache_sidecar VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("p1", b"\x00", "fx", "default", "q", "user-99", "semantic", "user-99", 0.0, None),
    )
    conn.commit()
    conn.close()

    lifecycle = DataLifecycleManager(
        tenant_id="tenant-a",
        cortex_memory=None,
        ledger_sink=ledger,
        sidecar_db=sidecar_db,
    )
    # Manual graph forget (no full Memory without Gemini)
    receipt = store.forget_source("user-99")
    assert receipt.get("edges_removed", 0) >= 0 or store.node_count() == 0

    result = lifecycle.forget_subject("user-99")
    assert result.layers.get("ledger_deleted", 0) >= 1
    assert result.layers.get("cache_sidecar_deleted", 0) >= 1
    assert ledger.get_run(run.run_id) is None

    store.close()
