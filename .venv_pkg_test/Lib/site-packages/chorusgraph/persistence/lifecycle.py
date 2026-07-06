"""Product-wide right-to-forget across layers (E5)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from chorusgraph.core.pending_writes import PendingWriteStore
from chorusgraph.ledger.sink import LedgerSink, SqliteLedgerSink


@dataclass
class ForgetResult:
    subject_id: str
    tenant_id: str
    layers: Dict[str, Any] = field(default_factory=dict)


class DataLifecycleManager:
    """Erase a subject's data across cortex graph, ledger, cache sidecar, and checkpoints."""

    def __init__(
        self,
        *,
        tenant_id: str,
        cortex_memory: Any = None,
        ledger_sink: Optional[LedgerSink] = None,
        sidecar_db: str | Path | None = None,
        pending_writes_root: str | Path | None = None,
        checkpoint_db: str | Path | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self._memory = cortex_memory
        self._ledger = ledger_sink
        self._sidecar_db = str(sidecar_db) if sidecar_db else None
        self._pending = PendingWriteStore(pending_writes_root) if pending_writes_root else None
        self._checkpoint_db = str(checkpoint_db) if checkpoint_db else None

    def forget_subject(self, subject_id: str) -> ForgetResult:
        result = ForgetResult(subject_id=subject_id, tenant_id=self.tenant_id)

        if self._memory is not None and hasattr(self._memory, "forget"):
            result.layers["cortex"] = self._memory.forget(subject_id)

        if self._ledger is not None and isinstance(self._ledger, SqliteLedgerSink):
            conn = self._ledger._conn
            cur = conn.execute(
                "DELETE FROM route_ledgers WHERE tenant_id = ? AND (turn_id = ? OR run_id = ?)",
                (self.tenant_id, subject_id, subject_id),
            )
            conn.commit()
            result.layers["ledger_deleted"] = cur.rowcount

        if self._sidecar_db:
            conn = sqlite3.connect(self._sidecar_db)
            cur = conn.execute(
                "DELETE FROM cache_sidecar WHERE scope_id = ? OR fingerprint_key = ?",
                (subject_id, subject_id),
            )
            conn.commit()
            result.layers["cache_sidecar_deleted"] = cur.rowcount
            conn.close()

        if self._pending is not None:
            # Clear pending writes for thread_id == subject_id
            root = self._pending._root
            thread_dir = root / subject_id.replace("/", "_").replace("\\", "_")
            if thread_dir.is_dir():
                import shutil

                shutil.rmtree(thread_dir, ignore_errors=True)
                result.layers["pending_writes_cleared"] = True

        if self._checkpoint_db and Path(self._checkpoint_db).exists():
            conn = sqlite3.connect(self._checkpoint_db)
            try:
                for table, sql in (
                    ("checkpoints", "DELETE FROM checkpoints WHERE thread_id = ?"),
                    ("writes", "DELETE FROM writes WHERE thread_id = ?"),
                ):
                    try:
                        cur = conn.execute(sql, (subject_id,))
                        result.layers[f"checkpoint_{table}_deleted"] = cur.rowcount
                    except sqlite3.OperationalError:
                        pass
                conn.commit()
            finally:
                conn.close()

        return result

    def register_subject_ref(self, db_path: str | Path, *, subject_id: str, layer: str, ref_key: str) -> None:
        conn = sqlite3.connect(str(db_path))
        from chorusgraph.persistence.migrations import migrate

        migrate(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO subject_data_index (tenant_id, subject_id, layer, ref_key)
            VALUES (?, ?, ?, ?)
            """,
            (self.tenant_id, subject_id, layer, ref_key),
        )
        conn.commit()
        conn.close()
