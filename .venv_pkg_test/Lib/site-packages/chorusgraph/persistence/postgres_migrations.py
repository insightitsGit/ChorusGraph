"""Postgres schema migrations for Cortex graph store (mirrors SQLite E5 migrations)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Tuple

MigrationFn = Callable[[Any], None]

MIGRATIONS: List[Tuple[int, str, MigrationFn]] = []


def migration(version: int, description: str):
    def decorator(fn: MigrationFn) -> MigrationFn:
        MIGRATIONS.append((version, description, fn))
        return fn

    return decorator


@migration(1, "schema_version table")
def _v1_schema_version(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )


@migration(2, "cortex graph persistence tables")
def _v2_cortex_graph(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cortex_graph_state (
            tenant_id TEXT NOT NULL,
            store_key TEXT NOT NULL DEFAULT 'default',
            version INTEGER NOT NULL DEFAULT 0,
            nodes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            edges_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            tombstones_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (tenant_id, store_key)
        )
        """
    )


@migration(3, "subject index for right-to-forget")
def _v3_subject_index(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subject_data_index (
            tenant_id TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            layer TEXT NOT NULL,
            ref_key TEXT NOT NULL,
            PRIMARY KEY (tenant_id, subject_id, layer, ref_key)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_subject_tenant
        ON subject_data_index (tenant_id, subject_id)
        """
    )


@dataclass
class MigrationResult:
    applied: List[int]
    current_version: int


def current_version(conn: Any) -> int:
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        return int(row[0] or 0)
    except Exception:
        return 0


def migrate(conn: Any, *, target: int | None = None) -> MigrationResult:
    applied: List[int] = []
    for version, description, fn in sorted(MIGRATIONS, key=lambda x: x[0]):
        if target is not None and version > target:
            break
        if version <= current_version(conn):
            continue
        fn(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, description) VALUES (%s, %s)",
            (version, description),
        )
        applied.append(version)
    return MigrationResult(applied=applied, current_version=current_version(conn))
