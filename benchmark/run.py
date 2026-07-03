"""A/B benchmark harness — dry-run and full workload execution."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

from benchmark.fl1.runner import FL1Runner
from benchmark.fc1.runner import FC1Runner
from benchmark.measure import ComparisonReport, TaskMeasurement
from benchmark.thresholds import THRESHOLD_PROVENANCE, measured_thresholds
from benchmark.workload import REPEAT_MODEL_DOC, generate_workload, workload_stats


def run_benchmark(
    n_tasks: int = 20,
    *,
    seed: int = 42,
    containers: Optional[List[str]] = None,
) -> ComparisonReport:
    """Run workload through both containers and collect measurements."""
    containers = containers or ["FL1", "FC1"]
    tasks = generate_workload(n_tasks, seed=seed)
    report = ComparisonReport(workload_size=len(tasks))
    report.notes.append(f"Workload stats: {workload_stats(tasks)}")
    report.notes.append(f"Thresholds: coarse={measured_thresholds().coarse}, verify={measured_thresholds().verify_for('fx_rates')}")

    runner_a = FL1Runner() if "FL1" in containers or "A" in containers else None
    runner_b = FC1Runner() if "FC1" in containers or "B" in containers else None

    for task in tasks:
        if runner_a:
            report.container_a.append(runner_a.run(task))
        if runner_b:
            report.container_b.append(runner_b.run(task))

    return report


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="ChorusGraph A/B benchmark harness (H8)")
    parser.add_argument("--tasks", type=int, default=20, help="Number of workload tasks (default: 20 dry-run)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--container", choices=["FL1", "FC1", "A", "B", "both"], default="both")
    parser.add_argument("--output", type=Path, default=None, help="Write JSON report to file")
    args = parser.parse_args(argv)

    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key

        if not resolve_gemini_api_key():
            print("Error: GEMINI_API_KEY required for benchmark dry-run.", file=sys.stderr)
            raise SystemExit(1)

    containers = (
        ["FL1", "FC1"]
        if args.container == "both"
        else ["FL1" if args.container in ("A", "FL1") else "FC1"]
    )
    print(f"Running finance single-agent benchmark: {args.tasks} tasks, scenarios={containers}")
    print(f"Repeat model:\n{REPEAT_MODEL_DOC}\n")
    print(f"Cache thresholds (B):\n{THRESHOLD_PROVENANCE}\n")

    report = run_benchmark(args.tasks, seed=args.seed, containers=containers)
    text = report.format_report()
    print(text)

    if args.output:
        payload = {
            "summary": report.summary(),
            "container_a": [r.to_dict() for r in report.container_a],
            "container_b": [r.to_dict() for r in report.container_b],
        }
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
