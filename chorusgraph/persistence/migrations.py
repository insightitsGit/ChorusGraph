"""Versioned schema migrations (ADR-003) for ChorusGraph stores (E5)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Tuple

MigrationFn = Callable[[sqlite3.Connection], None]

MIGRATIONS: List[Tuple[int, str, MigrationFn]] = []


def migration(version: int, description: str):
    def decorator(fn: MigrationFn) -> MigrationFn:
        MIGRATIONS.append((version, description, fn))
        return fn

    return decorator


@migration(1, "schema_version table")
def _v1_schema_version(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


@migration(2, "cortex graph persistence tables")
def _v2_cortex_graph(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cortex_graph_state (
            tenant_id TEXT NOT NULL,
            store_key TEXT NOT NULL DEFAULT 'default',
            version INTEGER NOT NULL DEFAULT 0,
            nodes_json TEXT NOT NULL DEFAULT '{}',
            edges_json TEXT NOT NULL DEFAULT '{}',
            tombstones_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (tenant_id, store_key)
        )
        """
    )


@migration(3, "subject index for right-to-forget")
def _v3_subject_index(conn: sqlite3.Connection) -> None:
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


def current_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        return int(row[0] or 0)
    except sqlite3.OperationalError:
        return 0


def migrate(conn: sqlite3.Connection, *, target: int | None = None) -> MigrationResult:
    """Apply pending forward migrations."""
    applied: List[int] = []
    for version, description, fn in sorted(MIGRATIONS, key=lambda x: x[0]):
        if target is not None and version > target:
            break
        if version <= current_version(conn):
            continue
        fn(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
            (version, description),
        )
        applied.append(version)
    conn.commit()
    return MigrationResult(applied=applied, current_version=current_version(conn))


def migrate_file(db_path: str | Path, *, target: int | None = None) -> MigrationResult:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        return migrate(conn, target=target)
    finally:
        conn.close()
