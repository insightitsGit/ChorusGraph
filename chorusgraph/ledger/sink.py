"""Pluggable durable sinks for Route Ledger persistence."""

from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional

from chorusgraph.ledger.models import LedgerStep, RouteLedger


class LedgerSink(ABC):
    """Interface for durable Route Ledger storage."""

    @abstractmethod
    def write(self, ledger: RouteLedger) -> None:
        """Persist a completed run ledger."""

    @abstractmethod
    def get_run(self, run_id: str) -> Optional[RouteLedger]:
        """Fetch a single run by id."""

    @abstractmethod
    def list_runs(
        self,
        *,
        graph_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[RouteLedger]:
        """List runs, optionally filtered."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS route_ledgers (
    run_id TEXT PRIMARY KEY,
    turn_id TEXT,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    steps_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_route_ledgers_graph_tenant
    ON route_ledgers (graph_id, tenant_id, created_at DESC);
"""


def _step_to_row(step: LedgerStep) -> dict:
    return {
        "node": step.node,
        "edge_taken": step.edge_taken,
        "rule_chain": step.rule_chain,
        "duration_ms": step.duration_ms,
        "timestamp": step.timestamp.isoformat(),
        "cache_hit": step.cache_hit,
        "cache_score": step.cache_score,
        "grounding_score": step.grounding_score,
        "error_code": step.error_code,
        "error_kind": step.error_kind,
        "retryable": step.retryable,
    }


def _row_to_step(data: dict) -> LedgerStep:
    ts = data.get("timestamp")
    timestamp = datetime.fromisoformat(ts) if ts else datetime.now().astimezone()
    return LedgerStep(
        node=data["node"],
        edge_taken=data.get("edge_taken"),
        rule_chain=data.get("rule_chain"),
        duration_ms=int(data.get("duration_ms") or 0),
        timestamp=timestamp,
        cache_hit=data.get("cache_hit"),
        cache_score=data.get("cache_score"),
        grounding_score=data.get("grounding_score"),
        error_code=data.get("error_code"),
        error_kind=data.get("error_kind"),
        retryable=data.get("retryable"),
    )


def _redact_ledger_for_persist(ledger: RouteLedger) -> RouteLedger:
    from chorusgraph.security.pii import redact_value

    return ledger.model_copy(
        update={
            "steps": [
                s.model_copy(update={"rule_chain": redact_value(s.rule_chain)}) for s in ledger.steps
            ]
        }
    )


def _ledger_to_row(ledger: RouteLedger) -> tuple:
    steps_json = json.dumps([_step_to_row(s) for s in ledger.steps])
    return (
        ledger.run_id,
        ledger.turn_id,
        ledger.tenant_id,
        ledger.graph_id,
        ledger.created_at.isoformat(),
        steps_json,
    )


def _row_to_ledger(row: tuple) -> RouteLedger:
    run_id, turn_id, tenant_id, graph_id, created_at, steps_json = row
    steps_data = json.loads(steps_json)
    return RouteLedger(
        run_id=run_id,
        turn_id=turn_id,
        tenant_id=tenant_id,
        graph_id=graph_id,
        created_at=datetime.fromisoformat(created_at),
        steps=[_row_to_step(s) for s in steps_data],
    )


class SqliteLedgerSink(LedgerSink):
    """Zero-config SQLite sink for local development."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        # Keep one connection so :memory: databases persist across operations.
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def write(self, ledger: RouteLedger) -> None:
        ledger = _redact_ledger_for_persist(ledger)
        self._conn.execute(
            """
            INSERT OR REPLACE INTO route_ledgers
                (run_id, turn_id, tenant_id, graph_id, created_at, steps_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            _ledger_to_row(ledger),
        )
        self._conn.commit()

    def get_run(self, run_id: str) -> Optional[RouteLedger]:
        row = self._conn.execute(
            "SELECT run_id, turn_id, tenant_id, graph_id, created_at, steps_json "
            "FROM route_ledgers WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return _row_to_ledger(row) if row else None

    def list_runs(
        self,
        *,
        graph_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[RouteLedger]:
        clauses: list[str] = []
        params: list[object] = []
        if graph_id is not None:
            clauses.append("graph_id = ?")
            params.append(graph_id)
        if tenant_id is not None:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        rows = self._conn.execute(
            f"""
            SELECT run_id, turn_id, tenant_id, graph_id, created_at, steps_json
            FROM route_ledgers
            {where}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [_row_to_ledger(r) for r in rows]


class PostgresLedgerSink(LedgerSink):
    """Production Postgres sink (DESIGN §5.3)."""

    def __init__(self, dsn: str) -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise ImportError(
                "PostgresLedgerSink requires psycopg. "
                "Install with: pip install 'chorusgraph[postgres]'"
            ) from exc
        self._dsn = dsn
        self._psycopg = psycopg
        self._init_db()

    @contextmanager
    def _connect(self):
        with self._psycopg.connect(self._dsn) as conn:
            yield conn
            conn.commit()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def write(self, ledger: RouteLedger) -> None:
        ledger = _redact_ledger_for_persist(ledger)
        row = _ledger_to_row(ledger)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO route_ledgers
                    (run_id, turn_id, tenant_id, graph_id, created_at, steps_json)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO UPDATE SET
                    turn_id = EXCLUDED.turn_id,
                    tenant_id = EXCLUDED.tenant_id,
                    graph_id = EXCLUDED.graph_id,
                    created_at = EXCLUDED.created_at,
                    steps_json = EXCLUDED.steps_json
                """,
                row,
            )

    def get_run(self, run_id: str) -> Optional[RouteLedger]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT run_id, turn_id, tenant_id, graph_id, created_at, steps_json "
                "FROM route_ledgers WHERE run_id = %s",
                (run_id,),
            ).fetchone()
        return _row_to_ledger(row) if row else None

    def list_runs(
        self,
        *,
        graph_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[RouteLedger]:
        clauses: list[str] = []
        params: list[object] = []
        if graph_id is not None:
            clauses.append("graph_id = %s")
            params.append(graph_id)
        if tenant_id is not None:
            clauses.append("tenant_id = %s")
            params.append(tenant_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT run_id, turn_id, tenant_id, graph_id, created_at, steps_json
                FROM route_ledgers
                {where}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                params,
            ).fetchall()
        return [_row_to_ledger(r) for r in rows]
