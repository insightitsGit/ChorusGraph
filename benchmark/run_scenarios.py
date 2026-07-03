"""Unified MVP scenario benchmark — FL1/FC1/HL1/HC1/FL2/FC2/HL2/HC2."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional

from benchmark.benchmark_flags import configure
from benchmark.cache_control import install_benchmark_cache_policy
from benchmark.compare_scenarios import compare_all_groups, format_comparison_report
from benchmark.healthcare_workload import HealthcareCase, generate_healthcare_workload
from benchmark.measure import TaskMeasurement
from benchmark.multiagent_measure import MultiAgentMeasurement
from benchmark.scenarios import ScenarioId, make_runner
from benchmark.workload import WorkloadTask, generate_workload

FINANCE_SINGLE = ("FL1", "FC1")
FINANCE_MULTI = ("FL2", "FC2")
HEALTHCARE_SINGLE = ("HL1", "HC1")
HEALTHCARE_MULTI = ("HL2", "HC2")
ALL_SCENARIOS: tuple[ScenarioId, ...] = FINANCE_SINGLE + FINANCE_MULTI + HEALTHCARE_SINGLE + HEALTHCARE_MULTI


def _is_finance(scenario: ScenarioId) -> bool:
    return scenario.startswith("F")


def _is_single(scenario: ScenarioId) -> bool:
    return scenario.endswith("1")


def run_scenarios(
    scenarios: List[ScenarioId],
    *,
    n_tasks: int = 12,
    seed: int = 42,
    repeat_band_pct: int = 40,
) -> Dict[str, List[Any]]:
    finance_tasks = generate_workload(n_tasks, seed=seed, repeat_band_pct=repeat_band_pct)
    healthcare_cases = generate_healthcare_workload(n_tasks, seed=seed, repeat_band_pct=repeat_band_pct)

    results: Dict[str, List[Any]] = {s: [] for s in scenarios}
    runners = {s: make_runner(s) for s in scenarios}

    for scenario in scenarios:
        runner = runners[scenario]
        if _is_finance(scenario):
            if _is_single(scenario):
                for task in finance_tasks:
                    row = runner.run(task)  # type: ignore[union-attr]
                    row.repeat_band_pct = repeat_band_pct
                    results[scenario].append(row)
            else:
                for task in finance_tasks:
                    results[scenario].append(runner.run(task))  # type: ignore[union-attr]
        else:
            if _is_single(scenario):
                for case in healthcare_cases:
                    results[scenario].append(runner.run(case))  # type: ignore[union-attr]
            else:
                for case in healthcare_cases:
                    results[scenario].append(runner.run(case))  # type: ignore[union-attr]

    return results


def _format_scenario_summary(scenario: str, stats: dict) -> str:
    """One-line human read: success, LLM calls, cache, latency."""
    if not stats:
        return f"{scenario}: (no data)"
    parts = [
        f"success={stats.get('task_success_rate', 0) * 100:.1f}%",
        f"llm_calls={stats.get('avg_llm_calls', 0):.2f}",
        f"cache_hit={stats.get('cache_hit_rate', 0) * 100:.1f}%",
        f"latency={stats.get('avg_latency_ms', 0):.0f}ms",
    ]
    if "abstain_rate" in stats:
        parts.insert(2, f"abstain={stats['abstain_rate'] * 100:.1f}%")
    return f"{scenario}: " + "  ".join(parts)


def aggregate_rows(rows: List[Any]) -> dict:
    if not rows:
        return {}
    if isinstance(rows[0], TaskMeasurement):
        cache_hits = [r for r in rows if r.cache_hit is True]
        return {
            "n": len(rows),
            "avg_latency_ms": round(mean(r.latency_ms for r in rows), 1),
            "avg_llm_calls": round(mean(r.llm_calls for r in rows), 2),
            "avg_tokens_in": round(mean(r.tokens_in for r in rows), 1),
            "task_success_rate": round(sum(1 for r in rows if r.task_success) / len(rows), 3),
            "cache_hit_rate": round(len(cache_hits) / len(rows), 3),
        }
    cache_hits = [r for r in rows if getattr(r, "cache_hit", None) is True]
    return {
        "n": len(rows),
        "avg_latency_ms": round(mean(r.latency_ms for r in rows), 1),
        "avg_llm_calls": round(mean(r.llm_calls for r in rows), 2),
        "avg_tokens_in": round(mean(r.tokens_in for r in rows), 1),
        "task_success_rate": round(sum(1 for r in rows if r.task_success) / len(rows), 3),
        "abstain_rate": round(sum(1 for r in rows if r.abstained) / len(rows), 3),
        "cache_hit_rate": round(len(cache_hits) / len(rows), 3) if rows else 0,
    }


def write_jsonl(path: Path, rows: List[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(asdict(row) if hasattr(row, "__dataclass_fields__") else row) + "\n")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="ChorusGraph MVP scenario benchmark")
    parser.add_argument(
        "--scenarios",
        default="all",
        help="Comma-separated scenario IDs (FL1,FC1,...) or: all, finance, healthcare, single, multi, pairs",
    )
    parser.add_argument("--tasks", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repeat-band", type=int, default=40)
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark/results/mvp_scenarios"))
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable semantic cache on ChorusGraph scenarios (FC*/HC*) — 0%% hit rate, full LLM path",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        default=True,
        help="Write group comparison report (LangGraph vs ChorusGraph per pair)",
    )
    parser.add_argument(
        "--no-compare",
        action="store_false",
        dest="compare",
        help="Skip comparison report",
    )
    args = parser.parse_args(argv)

    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key

        if not resolve_gemini_api_key():
            print("Error: GEMINI_API_KEY required.", file=sys.stderr)
            raise SystemExit(1)

    key = args.scenarios.lower().replace(" ", "")
    if key == "all":
        selected = list(ALL_SCENARIOS)
    elif key == "finance":
        selected = list(FINANCE_SINGLE + FINANCE_MULTI)
    elif key == "healthcare":
        selected = list(HEALTHCARE_SINGLE + HEALTHCARE_MULTI)
    elif key == "single":
        selected = list(FINANCE_SINGLE + HEALTHCARE_SINGLE)
    elif key == "multi":
        selected = list(FINANCE_MULTI + HEALTHCARE_MULTI)
    elif key == "pairs":
        selected = list(ALL_SCENARIOS)
    else:
        selected = [s.strip().upper() for s in args.scenarios.split(",") if s.strip()]

    for s in selected:
        if s not in ALL_SCENARIOS:
            print(f"Unknown scenario: {s}", file=sys.stderr)
            raise SystemExit(2)

    print(f"Running scenarios: {selected} ({args.tasks} tasks each, seed={args.seed})")
    configure(cache_enabled=not args.no_cache)
    install_benchmark_cache_policy()
    if args.no_cache:
        print("Cache: DISABLED (honest cold-path — expect 0% cache hits on C scenarios)")

    results = run_scenarios(selected, n_tasks=args.tasks, seed=args.seed, repeat_band_pct=args.repeat_band)

    out_dir = args.output_dir
    summary: Dict[str, Any] = {}
    for scenario, rows in results.items():
        write_jsonl(out_dir / f"{scenario.lower()}.jsonl", rows)
        summary[scenario] = aggregate_rows(rows)
        print(f"\n=== {scenario} ===")
        print(_format_scenario_summary(scenario, summary[scenario]))
        print(json.dumps(summary[scenario], indent=2))

    meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenarios": selected,
        "n_tasks": args.tasks,
        "seed": args.seed,
        "repeat_band_pct": args.repeat_band,
        "cache_enabled": not args.no_cache,
        "summary": summary,
    }

    if args.compare:
        comparison = compare_all_groups(results)
        meta["comparison"] = comparison
        (out_dir / "comparison.json").write_text(
            json.dumps(comparison, indent=2), encoding="utf-8"
        )
        report_md = format_comparison_report(comparison, cache_enabled=not args.no_cache)
        (out_dir / "COMPARISON_REPORT.md").write_text(report_md, encoding="utf-8")
        print("\n" + "=" * 72)
        try:
            print(report_md)
        except UnicodeEncodeError:
            # Windows console (cp1252) cannot render Δ/minus from the report table.
            print(report_md.encode("ascii", errors="replace").decode("ascii"))

    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nWrote results to {out_dir}")


if __name__ == "__main__":
    main()
