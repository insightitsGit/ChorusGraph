"""Query helpers for Route Ledger sinks."""

from __future__ import annotations

from typing import List, Optional

from chorusgraph.ledger.models import RouteLedger
from chorusgraph.ledger.sink import LedgerSink


def get_run(sink: LedgerSink, run_id: str) -> Optional[RouteLedger]:
    """Fetch a run's full ledger by run_id."""
    return sink.get_run(run_id)


def list_runs(
    sink: LedgerSink,
    *,
    graph_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    limit: int = 100,
) -> List[RouteLedger]:
    """List runs filtered by graph_id and/or tenant_id."""
    return sink.list_runs(graph_id=graph_id, tenant_id=tenant_id, limit=limit)
