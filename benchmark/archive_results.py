"""Archive benchmark run artifacts into tests/fixtures for reproducibility."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = REPO_ROOT / "benchmark" / "results"
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures" / "benchmark_results"

# Human-readable catalog of each run directory.
RUN_CATALOG: Dict[str, Dict[str, str]] = {
    "h10_volume": {
        "label": "H10 volume (pre-cache-seed-fix)",
        "valid_for_cache_thesis": "no",
        "notes": "1000 tasks x bands 40+60; cache_hit_rate 0% — ReAct never seeded cache.",
    },
    "cache_seed_pilot_40": {
        "label": "Cache seed fix pilot",
        "valid_for_cache_thesis": "yes",
        "notes": "40 tasks band 40; cache ~37.5% after ReAct seed fix; no memory tasks.",
    },
    "h10_slices_pilot_60": {
        "label": "H10 slices pilot (all fixes, 60 tasks)",
        "valid_for_cache_thesis": "yes",
        "notes": "Canonical post-fix run with slices, multi-phrase seed, cross-session memory, paraphrase forensics.",
    },
    "h10_final_pilot_40": {
        "label": "H10 final pilot (all fixes)",
        "valid_for_cache_thesis": "yes",
        "notes": "40 tasks; cache seed + cache_score + cross-session memory + density=2.",
    },
    "memory_pilot_40": {
        "label": "Memory + cache pilot (in-session recall)",
        "valid_for_cache_thesis": "yes",
        "notes": "40 tasks; same-session memory recall; belief calibration partial.",
    },
    "h9_full": {
        "label": "H9 full bands 20/40/60",
        "valid_for_cache_thesis": "no",
        "notes": "Pre-fix volume run; band 20 mostly novel.",
    },
    "h9_pilot": {
        "label": "H9 pilot band 40",
        "valid_for_cache_thesis": "no",
        "notes": "Early pilot before compound/rubric fixes.",
    },
    "h9_post_vector_fix": {
        "label": "H9 post vector fix live runs",
        "valid_for_cache_thesis": "partial",
        "notes": "30-task live A/B JSON snapshots.",
    },
}

SUMMARY_GLOBS = (
    "aggregate_analysis.json",
    "run_meta.json",
    "band_*_analysis.json",
    "run.log",
    "*.log",
)


def _collect_summary_files(run_dir: Path) -> List[Path]:
    found: List[Path] = []
    for pattern in SUMMARY_GLOBS:
        found.extend(run_dir.glob(pattern))
    # Top-level JSON in run dir (e.g. live_ab_30tasks.json)
    found.extend(p for p in run_dir.glob("*.json") if p.is_file())
    seen: set[str] = set()
    unique: List[Path] = []
    for path in sorted(found):
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _jsonl_line_counts(run_dir: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for path in sorted(run_dir.glob("*.jsonl")):
        counts[path.name] = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return counts


def archive_run(run_name: str, *, copy_jsonl: bool = False) -> Dict[str, Any]:
    src = RESULTS_ROOT / run_name
    if not src.is_dir():
        raise FileNotFoundError(f"Run directory not found: {src}")

    dest = FIXTURES_ROOT / run_name
    dest.mkdir(parents=True, exist_ok=True)

    copied: List[str] = []
    for path in _collect_summary_files(src):
        target = dest / path.name
        shutil.copy2(path, target)
        copied.append(path.name)

    if copy_jsonl:
        for path in src.glob("*.jsonl"):
            target = dest / path.name
            shutil.copy2(path, target)
            copied.append(path.name)

    meta = {
        "run_name": run_name,
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(src.relative_to(REPO_ROOT)).replace("\\", "/"),
        "files_copied": copied,
        "jsonl_line_counts": _jsonl_line_counts(src),
        **RUN_CATALOG.get(run_name, {"label": run_name, "notes": ""}),
    }
    (dest / "ARCHIVE_META.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def archive_all(*, copy_jsonl: bool = False) -> Dict[str, Any]:
    FIXTURES_ROOT.mkdir(parents=True, exist_ok=True)
    runs: List[Dict[str, Any]] = []
    for run_dir in sorted(RESULTS_ROOT.iterdir()):
        if not run_dir.is_dir():
            continue
        if run_dir.name.startswith("."):
            continue
        runs.append(archive_run(run_dir.name, copy_jsonl=copy_jsonl))

    # Root-level logs next to run folders
    for path in sorted(RESULTS_ROOT.glob("*.log")):
        target = FIXTURES_ROOT / "_logs" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    manifest = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "fixtures_root": str(FIXTURES_ROOT.relative_to(REPO_ROOT)).replace("\\", "/"),
        "source_root": str(RESULTS_ROOT.relative_to(REPO_ROOT)).replace("\\", "/"),
        "runs": runs,
        "code_milestones": {
            "cache_seed_react_fix": "ReAct path seeds semantic cache after fetch_exchange_rate",
            "cache_score_pattern_state": "PatternState includes cache_score for LangGraph propagation",
            "cross_session_memory": "memory_seed session N, memory_recall_cross session N+1",
            "memory_density_default": "memory_every_n_sessions=2",
        },
    }
    (FIXTURES_ROOT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Archive benchmark results to tests/fixtures")
    parser.add_argument("--run", type=str, default=None, help="Single run folder name under benchmark/results")
    parser.add_argument("--copy-jsonl", action="store_true", help="Also copy full JSONL (large)")
    args = parser.parse_args(argv)

    if args.run:
        meta = archive_run(args.run, copy_jsonl=args.copy_jsonl)
        print(json.dumps(meta, indent=2))
    else:
        manifest = archive_all(copy_jsonl=args.copy_jsonl)
        print(f"Archived {len(manifest['runs'])} runs -> {FIXTURES_ROOT}")
        print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
