"""Ingest prospect query logs (CSV / JSONL)."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

QUERY_COLUMN_CANDIDATES: tuple[str, ...] = (
    "query",
    "question",
    "prompt",
    "text",
    "message",
    "user_message",
    "input",
    "content",
    "user_query",
)

TIMESTAMP_COLUMN_CANDIDATES: tuple[str, ...] = (
    "timestamp",
    "ts",
    "created_at",
    "time",
    "date",
    "datetime",
    "logged_at",
)

TOKENS_IN_COLUMN_CANDIDATES: tuple[str, ...] = (
    "tokens_in",
    "prompt_tokens",
    "input_tokens",
    "tokens_input",
)

TOKENS_OUT_COLUMN_CANDIDATES: tuple[str, ...] = (
    "tokens_out",
    "completion_tokens",
    "output_tokens",
    "tokens_output",
)


@dataclass(frozen=True)
class LogRow:
    """One query from a prospect log."""

    query: str
    timestamp: Optional[datetime] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    row_index: int = 0


def detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return "jsonl"
    if suffix in (".csv", ".tsv"):
        return "csv"
    head = path.read_text(encoding="utf-8", errors="replace")[:4096].lstrip()
    if head.startswith("{") or head.startswith("["):
        return "jsonl"
    return "csv"


def _normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _pick_column(headers: Sequence[str], candidates: Sequence[str], explicit: Optional[str]) -> Optional[str]:
    if explicit:
        normalized = {_normalize_header(h): h for h in headers}
        key = _normalize_header(explicit)
        if key not in normalized:
            raise ValueError(f"Column {explicit!r} not found in log headers: {list(headers)}")
        return normalized[key]
    normalized = {_normalize_header(h): h for h in headers}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def _parse_timestamp(raw: Any) -> Optional[datetime]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        ts = float(raw)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts)
    text = str(raw).strip()
    if not text:
        return None
    if text.isdigit():
        ts = float(text)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_int(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        return int(float(str(raw).strip()))
    except (TypeError, ValueError):
        return None


def _rows_from_records(
    records: Iterable[dict[str, Any]],
    *,
    query_column: Optional[str],
    timestamp_column: Optional[str],
    tokens_in_column: Optional[str],
    tokens_out_column: Optional[str],
) -> List[LogRow]:
    records_list = list(records)
    if not records_list:
        return []

    headers = list(records_list[0].keys())
    q_col = _pick_column(headers, QUERY_COLUMN_CANDIDATES, query_column)
    if q_col is None:
        raise ValueError(
            "Could not auto-detect query column. Pass --query-column. "
            f"Tried: {', '.join(QUERY_COLUMN_CANDIDATES)}"
        )
    ts_col = _pick_column(headers, TIMESTAMP_COLUMN_CANDIDATES, timestamp_column)
    tin_col = _pick_column(headers, TOKENS_IN_COLUMN_CANDIDATES, None)
    tout_col = _pick_column(headers, TOKENS_OUT_COLUMN_CANDIDATES, None)
    if tokens_in_column:
        tin_col = _pick_column(headers, TOKENS_IN_COLUMN_CANDIDATES, tokens_in_column)
    if tokens_out_column:
        tout_col = _pick_column(headers, TOKENS_OUT_COLUMN_CANDIDATES, tokens_out_column)

    rows: list[LogRow] = []
    for idx, record in enumerate(records_list):
        query = str(record.get(q_col, "")).strip()
        if not query:
            continue
        rows.append(
            LogRow(
                query=query,
                timestamp=_parse_timestamp(record.get(ts_col)) if ts_col else None,
                tokens_in=_parse_int(record.get(tin_col)) if tin_col else None,
                tokens_out=_parse_int(record.get(tout_col)) if tout_col else None,
                row_index=idx,
            )
        )
    return rows


def load_jsonl(
    path: Path,
    *,
    query_column: Optional[str] = None,
    timestamp_column: Optional[str] = None,
    tokens_in_column: Optional[str] = None,
    tokens_out_column: Optional[str] = None,
) -> List[LogRow]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"JSONL rows must be objects (line {line_no})")
            records.append(obj)
    rows = _rows_from_records(
        records,
        query_column=query_column,
        timestamp_column=timestamp_column,
        tokens_in_column=tokens_in_column,
        tokens_out_column=tokens_out_column,
    )
    return _sort_rows(rows)


def load_csv(
    path: Path,
    *,
    query_column: Optional[str] = None,
    timestamp_column: Optional[str] = None,
    tokens_in_column: Optional[str] = None,
    tokens_out_column: Optional[str] = None,
) -> List[LogRow]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        if reader.fieldnames is None:
            return []
        records = [dict(row) for row in reader]
    rows = _rows_from_records(
        records,
        query_column=query_column,
        timestamp_column=timestamp_column,
        tokens_in_column=tokens_in_column,
        tokens_out_column=tokens_out_column,
    )
    return _sort_rows(rows)


def _sort_rows(rows: List[LogRow]) -> List[LogRow]:
    if not rows:
        return rows
    if any(r.timestamp is not None for r in rows):
        return sorted(
            rows,
            key=lambda r: (r.timestamp is None, r.timestamp or datetime.min, r.row_index),
        )
    return sorted(rows, key=lambda r: r.row_index)


def load_log(
    path: Path,
    *,
    fmt: Optional[str] = None,
    query_column: Optional[str] = None,
    timestamp_column: Optional[str] = None,
    tokens_in_column: Optional[str] = None,
    tokens_out_column: Optional[str] = None,
) -> List[LogRow]:
    resolved = (fmt or detect_format(path)).lower()
    if resolved == "jsonl":
        return load_jsonl(
            path,
            query_column=query_column,
            timestamp_column=timestamp_column,
            tokens_in_column=tokens_in_column,
            tokens_out_column=tokens_out_column,
        )
    if resolved == "csv":
        return load_csv(
            path,
            query_column=query_column,
            timestamp_column=timestamp_column,
            tokens_in_column=tokens_in_column,
            tokens_out_column=tokens_out_column,
        )
    raise ValueError(f"Unsupported format {resolved!r}; use csv or jsonl")


__all__ = [
    "LogRow",
    "QUERY_COLUMN_CANDIDATES",
    "TIMESTAMP_COLUMN_CANDIDATES",
    "detect_format",
    "load_log",
]
