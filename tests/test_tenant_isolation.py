"""E6 cross-tenant leakage and quota tests."""

from __future__ import annotations

import pytest

from chorusgraph.ledger.models import RouteLedger
from chorusgraph.ledger.sink import SqliteLedgerSink
from chorusgraph.persistence.sqlite_graph_store import SqliteGraphStore
from chorusgraph.security.cache import CacheSecurityGuard, CacheSecurityError
from chorusgraph.tenant import (
    TenantContext,
    TenantIsolationError,
    TenantResourceLimiter,
    assert_graph_read,
    safe_get_run,
)


def test_ledger_cross_tenant_read_denied(tmp_path):
    sink = SqliteLedgerSink(str(tmp_path / "ledger.db"))
    run = RouteLedger(tenant_id="tenant-a", graph_id="g1")
    sink.write(run)
    ctx_b = TenantContext(tenant_id="tenant-b")
    with pytest.raises(TenantIsolationError):
        safe_get_run(ctx_b, sink, run.run_id)


def test_cache_cross_tenant_write_denied():
    guard_a = CacheSecurityGuard(tenant_id="tenant-a")
    with pytest.raises(CacheSecurityError):
        guard_a.authorize_write(
            writer="cache_gate",
            entry_tenant_id="tenant-b",
            provenance={"run_id": "r1"},
        )


def test_graph_store_tenant_mismatch_denied(tmp_path):
    store = SqliteGraphStore(tmp_path / "g.db", tenant_id="tenant-a")
    ctx_b = TenantContext(tenant_id="tenant-b")
    with pytest.raises(TenantIsolationError):
        assert_graph_read(ctx_b, store)
    store.close()


def test_resource_limiter_blocks_burst():
    limiter = TenantResourceLimiter()
    tid = "noisy"
    for _ in range(16):
        limiter.acquire(tid)
    with pytest.raises(Exception):
        limiter.acquire(tid)


def test_tenant_scoped_keys_unique():
    a = TenantContext(tenant_id="tenant-a")
    b = TenantContext(tenant_id="tenant-b")
    assert a.scoped_key("cache:fx") != b.scoped_key("cache:fx")
