# Backup and Restore (E5)

## What to back up

| Store | Path (default) |
|-------|----------------|
| Cortex graph | `{cache_dir}/graph_store.db` |
| PrismLib cache | `{cache_dir}/prismlib.db` |
| Resonance state | `{cache_dir}/resonance_state.db` |
| Route Ledger | configured sink path |
| Checkpoints | `.chorusgraph/checkpoints/` |

## Backup

```python
from chorusgraph.persistence import backup_sqlite_stores, verify_backup_integrity

manifest = backup_sqlite_stores(
    target_dir=".chorusgraph/backups",
    sources=[
        ".chorusgraph/cortex/graph_store.db",
        ".chorusgraph/cortex/prismlib.db",
    ],
)
assert verify_backup_integrity(manifest.backup_dir)
```

## Restore

```python
from chorusgraph.persistence import restore_sqlite_store

restore_sqlite_store(
    ".chorusgraph/backups/backup_20260705T120000Z/graph_store.db",
    ".chorusgraph/cortex/graph_store.db",
)
```

Restart the process — graph state and cache reload from restored files.

## Migrations

```python
from chorusgraph.persistence import migrate_file

migrate_file(".chorusgraph/cortex/graph_store.db")
```

Migrations are forward-only and versioned in `schema_migrations`.

## Right-to-forget

```python
from chorusgraph.persistence import DataLifecycleManager

lifecycle = DataLifecycleManager(
    tenant_id="tenant-a",
    cortex_memory=cortex_service.ensure_memory(),
    ledger_sink=ledger_sink,
    sidecar_db=".chorusgraph/cache_sidecar.db",
)
lifecycle.forget_subject("user-subject-id")
```

Or via CortexMemoryService: `service.forget(source_id)`.
