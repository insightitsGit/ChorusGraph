"""Rebuild COMPARISON_REPORT.md and comparison.json from results.tar.gz or local JSONL."""

from __future__ import annotations

import argparse
import json
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from benchmark.compare_scenarios import compare_all_groups, format_comparison_report

SCENARIOS = ("FL1", "FC1", "FL2", "FC2", "HL1", "HC1", "HL2", "HC2")


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _jsonl_dir(run_dir: Path) -> Path:
    if (run_dir / "fl1.jsonl").exists():
        return run_dir
    for child in run_dir.iterdir():
        if child.is_dir() and (child / "fl1.jsonl").exists():
            return child
    tarball = run_dir / "results.tar.gz"
    if not tarball.exists():
        raise FileNotFoundError(f"No fl1.jsonl or results.tar.gz under {run_dir}")
    tmp = Path(tempfile.mkdtemp(prefix="rebuild_cmp_"))
    with tarfile.open(tarball, "r:gz") as tf:
        extract_kwargs: Dict[str, Any] = {}
        if hasattr(tarfile, "data_filter"):
            extract_kwargs["filter"] = "data"
        tf.extractall(tmp, **extract_kwargs)
    return _jsonl_dir(tmp)


def rebuild(run_dir: Path, *, cache_enabled: bool = True) -> Dict[str, Any]:
    data_dir = _jsonl_dir(run_dir)
    results: Dict[str, List[Dict[str, Any]]] = {}
    for sid in SCENARIOS:
        path = data_dir / f"{sid.lower()}.jsonl"
        if path.exists():
            results[sid] = _load_jsonl(path)
    comparison = compare_all_groups(results)
    report_md = format_comparison_report(comparison, cache_enabled=cache_enabled)
    run_dir.joinpath("COMPARISON_REPORT.md").write_text(report_md, encoding="utf-8")
    run_meta_path = run_dir / "run_meta.json"
    if run_meta_path.exists():
        meta = json.loads(run_meta_path.read_text(encoding="utf-8"))
        meta["comparison"] = comparison
        run_meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return comparison


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="Directory with results.tar.gz or *.jsonl")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Pass cache_enabled=False to report banner (default: true)",
    )
    args = parser.parse_args()
    rebuild(args.run_dir.resolve(), cache_enabled=not args.no_cache)
    print(f"Rebuilt {args.run_dir / 'COMPARISON_REPORT.md'}")


if __name__ == "__main__":
    main()
