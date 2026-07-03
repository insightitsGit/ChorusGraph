"""Structured trace logging for HC2 — hop-level execution visibility."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

_TRACE_ENABLED = os.environ.get("CHORUS_D_TRACE", "1").strip().lower() not in ("0", "false", "no")
_TRACE_PATH = Path(
    os.environ.get(
        "CHORUS_D_TRACE_PATH",
        "benchmark/results/d_trace/container_d_trace.jsonl",
    )
)


def trace_path() -> Path:
    return _TRACE_PATH


def trace_event(
    event: str,
    *,
    case_id: str = "",
    session_id: str = "",
    hop: str = "",
    **fields: Any,
) -> None:
    if not _TRACE_ENABLED:
        return
    row: dict[str, Any] = {"ts": time.time(), "event": event}
    if case_id:
        row["case_id"] = case_id
    if session_id:
        row["session_id"] = session_id
    if hop:
        row["hop"] = hop
    for key, value in fields.items():
        if value is not None:
            row[key] = value
    _TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _TRACE_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def clear_trace() -> None:
    if _TRACE_PATH.exists():
        _TRACE_PATH.unlink()
