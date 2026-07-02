"""H12 regression gate — diff per-task answers vs a baseline JSONL run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def _load(path: Path, container: str) -> Dict[str, dict]:
    rows: Dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("container") != container:
            continue
        rows[row["task_id"]] = row
    return rows


def compare_runs(
    baseline_path: Path,
    candidate_path: Path,
    *,
    container: str = "B",
) -> Tuple[List[str], dict]:
    base = _load(baseline_path, container)
    cand = _load(candidate_path, container)
    errors: List[str] = []
    stats = {
        "n_baseline": len(base),
        "n_candidate": len(cand),
        "n_compared": 0,
        "answer_mismatches": 0,
        "success_mismatches": 0,
        "cache_hit_mismatches": 0,
    }

    for task_id, brow in base.items():
        crow = cand.get(task_id)
        if crow is None:
            errors.append(f"{task_id}: missing in candidate")
            continue
        stats["n_compared"] += 1
        if brow.get("task_success") != crow.get("task_success"):
            stats["success_mismatches"] += 1
            errors.append(
                f"{task_id}: task_success {brow.get('task_success')} -> {crow.get('task_success')}"
            )
        if brow.get("cache_hit") != crow.get("cache_hit"):
            stats["cache_hit_mismatches"] += 1
            errors.append(
                f"{task_id}: cache_hit {brow.get('cache_hit')} -> {crow.get('cache_hit')}"
            )
        if (brow.get("answer") or "") != (crow.get("answer") or ""):
            stats["answer_mismatches"] += 1
            errors.append(f"{task_id}: answer mismatch")

    return errors, stats


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare benchmark JSONL runs (H12 regression gate)")
    parser.add_argument("baseline", type=Path, help="Baseline JSONL (e.g. h11 band_40_container_b.jsonl)")
    parser.add_argument("candidate", type=Path, help="Candidate JSONL after refactor")
    parser.add_argument("--container", default="B", choices=("A", "B"))
    args = parser.parse_args(argv)

    errors, stats = compare_runs(args.baseline, args.candidate, container=args.container)
    print(json.dumps(stats, indent=2))
    if errors:
        print(f"\n{len(errors)} difference(s):", file=sys.stderr)
        for e in errors[:50]:
            print(f"  {e}", file=sys.stderr)
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more", file=sys.stderr)
        raise SystemExit(1)
    print("PASS — byte-identical answers, task_success, and cache_hit per task.")


if __name__ == "__main__":
    main()
