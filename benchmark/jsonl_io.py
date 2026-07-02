"""JSONL persistence for benchmark runs."""

from __future__ import annotations

import json
import os
from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, Iterable, List

from benchmark.measure import TaskMeasurement


def append_measurement(path: Path, row: TaskMeasurement) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row.to_dict(), ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())


def load_measurements(path: Path) -> List[TaskMeasurement]:
    if not path.exists():
        return []
    by_key: Dict[str, TaskMeasurement] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        allowed = {f.name for f in fields(TaskMeasurement)}
        row = TaskMeasurement(**{k: v for k, v in data.items() if k in allowed})
        by_key[f"{row.container}:{row.task_id}"] = row
    return list(by_key.values())


def completed_task_ids(paths: Iterable[Path]) -> set[str]:
    done: set[str] = set()
    for path in paths:
        for row in load_measurements(path):
            done.add(f"{row.container}:{row.task_id}")
    return done
