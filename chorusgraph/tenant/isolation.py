"""Cross-layer tenant isolation helpers (E6)."""

from __future__ import annotations

from typing import Any, Optional

from chorusgraph.ledger.sink import LedgerSink
from chorusgraph.persistence.sqlite_graph_store import SqliteGraphStore
from chorusgraph.security.cache import CacheSecurityGuard
from chorusgraph.tenant.context import TenantContext, TenantIsolationError


def assert_ledger_read(ctx: TenantContext, ledger_tenant_id: str) -> None:
    ctx.assert_match(ledger_tenant_id, layer="ledger")


def assert_cache_read(ctx: TenantContext, entry_tenant_id: str) -> None:
    CacheSecurityGuard(tenant_id=ctx.tenant_id).assert_read_scope(entry_tenant_id)


def assert_graph_read(ctx: TenantContext, store: SqliteGraphStore) -> None:
    if store._tenant_id != ctx.tenant_id:
        raise TenantIsolationError(
            f"Cross-tenant graph access: requester={ctx.tenant_id} store={store._tenant_id}"
        )


def safe_get_run(ctx: TenantContext, sink: LedgerSink, run_id: str) -> Optional[Any]:
    run = sink.get_run(run_id)
    if run is None:
        return None
    assert_ledger_read(ctx, run.tenant_id)
    return run
