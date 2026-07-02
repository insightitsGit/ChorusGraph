"""H9 volume benchmark — repeat-band sensitivity, JSONL persistence, analysis."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from benchmark.analyze import compare_ab, format_ci_table
from benchmark.belief_calibration import calibrate_from_measurements
from benchmark.container_a.runner import ContainerARunner
from benchmark.container_b.runner import ContainerBRunner
from benchmark.jsonl_io import append_measurement, completed_task_ids, load_measurements
from benchmark.measure import TaskMeasurement
from benchmark.thresholds import THRESHOLD_PROVENANCE, measured_thresholds
from benchmark.workload import REPEAT_BANDS, generate_workload, workload_stats


def _results_dir(base: Path) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    return base


def run_band(
    *,
    band_pct: int,
    n_tasks: int,
    seed: int,
    out_dir: Path,
    resume: bool = True,
) -> Dict[str, object]:
    tasks = generate_workload(n_tasks, seed=seed, repeat_band_pct=band_pct)
    path_a = out_dir / f"band_{band_pct}_container_a.jsonl"
    path_b = out_dir / f"band_{band_pct}_container_b.jsonl"

    done = completed_task_ids([path_a, path_b]) if resume else set()
    runner_a = ContainerARunner()
    runner_b = ContainerBRunner()

    started = time.perf_counter()
    for i, task in enumerate(tasks):
        key_a = f"A:{task.task_id}"
        key_b = f"B:{task.task_id}"

        def _run_a() -> None:
            if key_a in done:
                return
            row_a = runner_a.run(task)
            row_a.repeat_band_pct = band_pct
            row_a.category_slug = task.category_slug
            row_a.reasoning_path = "langgraph/react"
            append_measurement(path_a, row_a)

        def _run_b() -> None:
            if key_b in done:
                return
            row_b = runner_b.run(task)
            row_b.repeat_band_pct = band_pct
            row_b.category_slug = task.category_slug
            append_measurement(path_b, row_b)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(_run_a), pool.submit(_run_b)]
            for fut in futures:
                fut.result()

        if (i + 1) % 25 == 0:
            elapsed = time.perf_counter() - started
            print(f"  band {band_pct}%: {i + 1}/{n_tasks} tasks ({elapsed:.0f}s elapsed)")

    a_rows = load_measurements(path_a)
    b_rows = load_measurements(path_b)
    comparison = compare_ab(a_rows, b_rows)
    calibration = calibrate_from_measurements(b_rows)

    band_report = {
        "repeat_band_pct": band_pct,
        "n_tasks": n_tasks,
        "seed": seed,
        "workload_stats": workload_stats(tasks),
        "compare_ab": comparison,
        "belief_calibration": calibration.to_dict(),
        "thresholds": {
            "coarse": measured_thresholds().coarse,
            "verify_fx_rates": measured_thresholds().verify_for("fx_rates"),
        },
    }
    report_path = out_dir / f"band_{band_pct}_analysis.json"
    report_path.write_text(json.dumps(band_report, indent=2), encoding="utf-8")
    return band_report


def run_volume_benchmark(
    *,
    bands: List[int],
    n_tasks: int = 1000,
    seed: int = 42,
    out_dir: Optional[Path] = None,
    resume: bool = True,
) -> Dict[str, object]:
    out_dir = _results_dir(out_dir or Path("benchmark/results") / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
    meta = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "environment": os.environ.get("BENCHMARK_ENV", "local"),
        "n_tasks_per_band": n_tasks,
        "bands": bands,
        "seed": seed,
        "threshold_provenance": THRESHOLD_PROVENANCE,
        "fairness_doc": "benchmark/FAIRNESS_H9.md",
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    band_results: Dict[int, Dict[str, object]] = {}
    all_b: List[TaskMeasurement] = []

    for band in bands:
        print(f"\n=== Repeat band {band}% — {n_tasks} tasks ===")
        band_results[band] = run_band(
            band_pct=band,
            n_tasks=n_tasks,
            seed=seed + band,
            out_dir=out_dir,
            resume=resume,
        )
        all_b.extend(load_measurements(out_dir / f"band_{band}_container_b.jsonl"))

    aggregate = {
        "meta": meta,
        "bands": band_results,
        "belief_calibration_pooled": calibrate_from_measurements(all_b).to_dict(),
        "ci_table_markdown": format_ci_table({b: {"compare_ab": band_results[b]["compare_ab"]} for b in bands}),
    }
    (out_dir / "aggregate_analysis.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    aggregate["output_dir"] = str(out_dir)
    return aggregate


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="H9 volume A/B benchmark")
    parser.add_argument("--tasks", type=int, default=1000, help="Tasks per repeat band (default 1000)")
    parser.add_argument("--bands", type=str, default="20,40,60", help="Comma-separated repeat bands")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)

    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key

        if not resolve_gemini_api_key():
            print("Error: GEMINI_API_KEY required.", file=sys.stderr)
            raise SystemExit(1)

    bands = [int(b.strip()) for b in args.bands.split(",")]
    for b in bands:
        if b not in REPEAT_BANDS:
            raise SystemExit(f"Invalid band {b}; must be in {sorted(REPEAT_BANDS)}")

    print("H9 volume benchmark — fairness verified per benchmark/FAIRNESS_H9.md")
    print(f"B uses ReAct/AgentNode path; thresholds: {measured_thresholds().coarse}/{measured_thresholds().verify_for('fx_rates')}")

    result = run_volume_benchmark(
        bands=bands,
        n_tasks=args.tasks,
        seed=args.seed,
        out_dir=args.output_dir,
        resume=not args.no_resume,
    )
    print(f"\nDone. Results: {result['output_dir']}")
    print("\nCI table preview:\n")
    print(result.get("ci_table_markdown", ""))


if __name__ == "__main__":
    main()
