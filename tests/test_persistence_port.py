"""PersistenceBackend port — 5th ChorusStack swappable port."""

from __future__ import annotations

import dataclasses

import pytest

from chorusgraph.compose import ChorusStack
from chorusgraph.compose.adapters.persistence import (
    PostgresPersistenceBackend,
    SqlitePersistenceBackend,
)
from chorusgraph.licensing import ENTERPRISE_PERSISTENCE, LicenseError
from tests.support.license_fixture import write_test_license


def test_resolve_persistence_defaults_to_sqlite():
    stack = ChorusStack.defaults(tenant_id="persist-default")
    backend = stack.resolve_persistence()
    assert isinstance(backend, SqlitePersistenceBackend)
    assert backend.name == "sqlite"
    cp = stack.resolve_checkpointer()
    assert cp is not None


def test_with_persistence_preserves_all_fields():
    stack = ChorusStack.defaults(tenant_id="persist-fields", enable_memory=False)
    pg = PostgresPersistenceBackend(dsn="postgresql://example")
    swapped = stack.with_persistence(pg)
    for fld in dataclasses.fields(ChorusStack):
        if fld.name in ("persistence", "checkpointer"):
            continue
        assert getattr(swapped, fld.name) == getattr(stack, fld.name)
    assert swapped.persistence is pg
    assert swapped.checkpointer is None


def test_unlicensed_postgres_checkpointer_raises():
    backend = PostgresPersistenceBackend(dsn="postgresql://localhost/test")
    with pytest.raises(LicenseError, match="CHORUSGRAPH_LICENSE_FILE"):
        backend.make_checkpointer(checkpoint_root=".chorusgraph/checkpoints")


def test_licensed_postgres_checkpointer_requires_psycopg(tmp_path, monkeypatch):
    lic = write_test_license(tmp_path / "lic.json", features=[ENTERPRISE_PERSISTENCE])
    monkeypatch.setenv("CHORUSGRAPH_LICENSE_FILE", str(lic))
    backend = PostgresPersistenceBackend(dsn="postgresql://localhost:5432/test")
    pytest.importorskip("psycopg")
    try:
        backend.make_checkpointer(checkpoint_root=str(tmp_path / "cp"))
    except Exception as exc:
        # Connection failure is fine — license gate passed
        assert "CHORUSGRAPH_LICENSE_FILE" not in str(exc)


def test_stack_with_sqlite_graph_store(tmp_path):
    stack = ChorusStack.defaults(tenant_id="graph-t", cortex_cache_dir=str(tmp_path))
    store = stack.resolve_graph_store(graph_path=str(tmp_path / "g.db"))
    from chorusgraph.persistence.sqlite_graph_store import SqliteGraphStore

    assert isinstance(store, SqliteGraphStore)
    store.close()
