"""E5 durable persistence — graph store, migrations, backup, lifecycle."""

from chorusgraph.persistence.backup import BackupManifest, backup_sqlite_stores, restore_sqlite_store, verify_backup_integrity
from chorusgraph.persistence.cortex_factory import create_durable_prism_memory, graph_db_path
from chorusgraph.persistence.lifecycle import DataLifecycleManager, ForgetResult
from chorusgraph.persistence.migrations import MigrationResult, migrate, migrate_file
from chorusgraph.persistence.postgres_graph_store import PostgresGraphStore
from chorusgraph.persistence.sqlite_graph_store import SqliteGraphStore

__all__ = [
    "BackupManifest",
    "DataLifecycleManager",
    "ForgetResult",
    "MigrationResult",
    "PostgresGraphStore",
    "SqliteGraphStore",
    "backup_sqlite_stores",
    "create_durable_prism_memory",
    "graph_db_path",
    "migrate",
    "migrate_file",
    "restore_sqlite_store",
    "verify_backup_integrity",
]
