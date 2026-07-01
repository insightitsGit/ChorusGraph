"""PrismCheckpointer — LangGraph checkpointer factory (SQLite / Postgres)."""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Literal, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver


def sqlite_checkpointer(
    path: str = ".chorusgraph/checkpoints.sqlite",
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> BaseCheckpointSaver:
    """Create a SQLite-backed checkpointer for local dev and demos."""
    from langgraph.checkpoint.sqlite import SqliteSaver

    if conn is None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
    return SqliteSaver(conn)


def postgres_checkpointer(conn_string: str) -> BaseCheckpointSaver:
    """Create a Postgres-backed checkpointer (requires langgraph-checkpoint-postgres)."""
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
    except ImportError as exc:
        raise ImportError(
            "Postgres checkpointer requires langgraph-checkpoint-postgres. "
            "Install with: pip install chorusgraph[postgres-checkpoint]"
        ) from exc

    return PostgresSaver.from_conn_string(conn_string)


def create_checkpointer(
    backend: Literal["sqlite", "postgres"] = "sqlite",
    *,
    path: str = ".chorusgraph/checkpoints.sqlite",
    conn: Optional[sqlite3.Connection] = None,
    conn_string: Optional[str] = None,
) -> BaseCheckpointSaver:
    """Factory for PrismCheckpointer backends."""
    if backend == "sqlite":
        return sqlite_checkpointer(path, conn=conn)
    if backend == "postgres":
        if not conn_string:
            raise ValueError("conn_string is required for postgres backend")
        return postgres_checkpointer(conn_string)
    raise ValueError(f"Unknown checkpointer backend: {backend}")


def PrismCheckpointer(
    backend: Literal["sqlite", "postgres"] = "sqlite",
    **kwargs: Any,
) -> BaseCheckpointSaver:
    """Alias for create_checkpointer — DESIGN §5.3 PrismCheckpointer."""
    return create_checkpointer(backend, **kwargs)
