"""Load hub query-log JSONL exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, List

from chorusgraph.shadow.replay.schema import TurnRecord


def load_jsonl(path: Path | str) -> List[TurnRecord]:
    """Load turns from JSONL; one JSON object per line."""
    records: list[TurnRecord] = []
    with Path(path).open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_no}") from exc
            records.append(TurnRecord.from_json(data))
    records.sort(key=lambda r: r.timestamp)
    return records


def iter_jsonl(path: Path | str) -> Iterator[TurnRecord]:
    return iter(load_jsonl(path))
