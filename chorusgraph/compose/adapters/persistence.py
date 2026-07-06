"""Persistence port adapters — SQLite (free default) and Postgres (enterprise)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union

from chorusgraph.compose.ports import PersistenceBackend
from chorusgraph.core.persistence import EngineCheckpointer, json_file_checkpointer, postgres_checkpointer
from chorusgraph.persistence.sqlite_graph_store import SqliteGraphStore


@dataclass(frozen=True)
class SqlitePersistenceBackend:
    """Free default — JSON checkpoints + SQLite Cortex graph (single-instance)."""

    name: str = "sqlite"

    def make_checkpointer(self, *, checkpoint_root: str) -> EngineCheckpointer:
        return json_file_checkpointer(checkpoint_root)

    def make_graph_store(self, *, graph_path: str, tenant_id: str) -> SqliteGraphStore:
        return SqliteGraphStore(graph_path, tenant_id=tenant_id)


@dataclass(frozen=True)
class PostgresPersistenceBackend:
    """Enterprise — Postgres checkpoints + graph store (multi-replica safe)."""

    dsn: str
    name: str = "postgres"
    pending_writes_root: str | None = None

    def make_checkpointer(self, *, checkpoint_root: str) -> EngineCheckpointer:
        del checkpoint_root  # Postgres uses DSN; pending writes may use local dir
        return postgres_checkpointer(
            self.dsn,
            pending_writes_root=self.pending_writes_root,
        )

    def make_graph_store(self, *, graph_path: str, tenant_id: str) -> Any:
        del graph_path  # graph lives in Postgres DSN
        from chorusgraph.persistence.postgres_graph_store import PostgresGraphStore

        return PostgresGraphStore(self.dsn, tenant_id=tenant_id)


GraphStoreLike = Union[SqliteGraphStore, Any]

__all__ = [
    "GraphStoreLike",
    "PostgresPersistenceBackend",
    "SqlitePersistenceBackend",
]
