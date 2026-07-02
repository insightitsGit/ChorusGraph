"""Dedupe benchmark JSONL files in place (keep last row per container:task_id)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def dedupe_file(path: Path) -> int:
    if not path.exists():
        return 0
    by_key: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = f"{data.get('container')}:{data.get('task_id')}"
        by_key[key] = line
    path.write_text("\n".join(by_key.values()) + ("\n" if by_key else ""), encoding="utf-8")
    return len(by_key)


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "benchmark/results/h9_full")
    for path in sorted(target.glob("band_*_container_*.jsonl")):
        n = dedupe_file(path)
        print(f"{path.name}: {n} unique rows")
