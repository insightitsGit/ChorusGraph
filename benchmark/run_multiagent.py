"""Multi-agent C vs D benchmark harness — depth sweep + per-hop metrics."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional

from benchmark.container_c.runner import ContainerCRunner
from benchmark.container_d.runner import ContainerDRunner
from benchmark.healthcare_workload import HealthcareCase, generate_healthcare_workload
from benchmark.multiagent_measure import MultiAgentMeasurement


def run_multiagent_benchmark(
    n_cases: int = 18,
    *,
    seed: int = 42,
    containers: Optional[List[str]] = None,
) -> Dict[str, List[MultiAgentMeasurement]]:
    containers = containers or ["C", "D"]
    cases = generate_healthcare_workload(n_cases, seed=seed)
    results: Dict[str, List[MultiAgentMeasurement]] = {"C": [], "D": []}
    runner_c = ContainerCRunner() if "C" in containers else None
    runner_d = ContainerDRunner() if "D" in containers else None

    for case in cases:
        if runner_c:
            results["C"].append(runner_c.run(case))
        if runner_d:
            results["D"].append(runner_d.run(case))

    return results


def aggregate_by_depth(rows: List[MultiAgentMeasurement]) -> Dict[int, dict]:
    buckets: Dict[int, List[MultiAgentMeasurement]] = defaultdict(list)
    for row in rows:
        buckets[row.pipeline_depth].append(row)

    out: Dict[int, dict] = {}
    for depth, items in sorted(buckets.items()):
        hop_totals: Dict[str, dict] = defaultdict(lambda: {"latency_ms": 0, "tokens_in": 0, "tokens_out": 0, "llm_calls": 0})
        for item in items:
            for hop in item.hop_metrics:
                hop_totals[hop.hop]["latency_ms"] += hop.latency_ms
                hop_totals[hop.hop]["tokens_in"] += hop.tokens_in
                hop_totals[hop.hop]["tokens_out"] += hop.tokens_out
                hop_totals[hop.hop]["llm_calls"] += hop.llm_calls

        total_tokens_in = [i.tokens_in for i in items]
        out[depth] = {
            "n": len(items),
            "avg_latency_ms": round(mean(i.latency_ms for i in items), 1),
            "avg_total_tokens_in": round(mean(total_tokens_in), 1),
            "avg_tokens_in": round(mean(total_tokens_in), 1),
            "avg_tokens_out": round(mean(i.tokens_out for i in items), 1),
            "avg_cost_usd": round(mean(i.cost_usd for i in items), 6),
            "avg_tool_calls": round(mean(i.tool_calls for i in items), 2),
            "task_success_rate": round(sum(1 for i in items if i.task_success) / len(items), 3),
            "abstain_rate": round(sum(1 for i in items if i.abstained) / len(items), 3),
            "avg_embed_count": round(mean(i.embed_count for i in items), 2) if items else 0,
            "avg_hop_latency_ms": {k: round(v["latency_ms"] / len(items), 1) for k, v in hop_totals.items()},
            "avg_hop_tokens_in": {k: round(v["tokens_in"] / len(items), 1) for k, v in hop_totals.items()},
        }
    return out


def format_report(results: Dict[str, List[MultiAgentMeasurement]]) -> str:
    lines = ["# Multi-agent C vs D dry-run", ""]
    for container in ("C", "D"):
        rows = results.get(container, [])
        if not rows:
            continue
        lines.append(f"## Container {container} (n={len(rows)})")
        agg = aggregate_by_depth(rows)
        for depth, stats in sorted(agg.items()):
            lines.append(
                f"- depth={depth}: latency={stats['avg_latency_ms']}ms "
                f"tokens_in={stats['avg_tokens_in']} cost=${stats['avg_cost_usd']} "
                f"tools={stats['avg_tool_calls']} success={stats['task_success_rate']} "
                f"abstain={stats['abstain_rate']}"
                + (
                    f" embeds={stats['avg_embed_count']}"
                    if stats.get("avg_embed_count")
                    else ""
                )
            )
        lines.append("")
    return "\n".join(lines)


def write_jsonl(path: Path, rows: List[MultiAgentMeasurement]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Healthcare multi-agent C vs D harness (H13)")
    parser.add_argument("--cases", type=int, default=18, help="Cases across depth sweep (default 18)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--container", choices=["C", "D", "both"], default="both")
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark/results/h13_multiagent_dryrun"))
    args = parser.parse_args(argv)

    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key

        if not resolve_gemini_api_key():
            print("Error: GEMINI_API_KEY required for multi-agent dry-run.", file=sys.stderr)
            raise SystemExit(1)

    containers = ["C", "D"] if args.container == "both" else [args.container]
    print(f"Running multi-agent dry-run: {args.cases} cases, containers={containers}")
    results = run_multiagent_benchmark(args.cases, seed=args.seed, containers=containers)
    print(format_report(results))

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "run_label": "H13_multiagent_dryrun",
        "n_cases": args.cases,
        "seed": args.seed,
        "containers": containers,
        "aggregate": {c: aggregate_by_depth(rows) for c, rows in results.items()},
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    for container, rows in results.items():
        write_jsonl(out_dir / f"container_{container.lower()}.jsonl", rows)
    print(f"\nWrote results to {out_dir}")


if __name__ == "__main__":
    main()
