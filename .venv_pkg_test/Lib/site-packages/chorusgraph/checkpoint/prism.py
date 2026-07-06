"""PrismCheckpointer — native prismlang persistence."""

from __future__ import annotations

import warnings
from typing import Any, Literal, Optional

from chorusgraph.core.persistence import (
    EngineCheckpointer,
    json_file_checkpointer,
    postgres_checkpointer as engine_postgres_checkpointer,
)


def _json_backend(path: str = ".chorusgraph/checkpoints") -> Any:
    from prismlang import JsonFileCheckpointer

    return JsonFileCheckpointer(path)


def sqlite_checkpointer(
    path: str = ".chorusgraph/checkpoints",
    *,
    conn: Any = None,
) -> Any:
    """
    Deprecated alias for file-backed checkpointing.

    ``conn`` is ignored — use ``json_file_checkpointer`` or ``postgres_checkpointer``.
    """
    _ = conn
    warnings.warn(
        "sqlite_checkpointer is file-backed; use json_file_checkpointer or postgres_checkpointer",
        DeprecationWarning,
        stacklevel=2,
    )
    return _json_backend(path)


def engine_checkpointer(path: str = ".chorusgraph/checkpoints") -> EngineCheckpointer:
    """Native engine wrapper for ``CompiledGraph`` checkpoint boundaries."""
    return json_file_checkpointer(path)


def postgres_checkpointer(conn_string: str) -> EngineCheckpointer:
    """Postgres checkpointer wrapped for ``chorusgraph.core.Graph``."""
    return engine_postgres_checkpointer(conn_string)


def create_checkpointer(
    backend: Literal["sqlite", "json", "postgres"] = "json",
    *,
    path: str = ".chorusgraph/checkpoints",
    conn: Any = None,
    conn_string: Optional[str] = None,
    native: bool = False,
) -> Any:
    """
    Factory for checkpointers.

    ``native=True`` returns ``EngineCheckpointer`` for ``chorusgraph.Graph``.
    Default returns prismlang backend for LangGraph-compatible graphs.
    """
    if native:
        return engine_checkpointer(path)
    if backend in ("sqlite", "json"):
        if backend == "sqlite":
            return sqlite_checkpointer(path, conn=conn)
        return _json_backend(path)
    if backend == "postgres":
        if not conn_string:
            raise ValueError("conn_string is required for postgres backend")
        return postgres_checkpointer(conn_string)
    raise ValueError(f"Unknown checkpointer backend: {backend}")


def PrismCheckpointer(
    backend: Literal["sqlite", "json", "postgres"] = "json",
    **kwargs: Any,
) -> Any:
    """Alias for create_checkpointer — DESIGN §5.3 PrismCheckpointer."""
    return create_checkpointer(backend, **kwargs)


__all__ = [
    "EngineCheckpointer",
    "PrismCheckpointer",
    "create_checkpointer",
    "engine_checkpointer",
    "json_file_checkpointer",
    "postgres_checkpointer",
    "sqlite_checkpointer",
]
