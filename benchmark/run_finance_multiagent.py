"""Finance multi-agent E vs F benchmark — same workload as A/B, linear multi-hop pipeline."""

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

from benchmark.container_e.runner import ContainerERunner
from benchmark.container_f.runner import ContainerFRunner
from benchmark.measure import TaskMeasurement
from benchmark.workload import WorkloadTask, generate_workload, workload_stats


def run_finance_multiagent(
    n_tasks: int = 60,
    *,
    seed: int = 42,
    repeat_band_pct: int = 40,
    containers: Optional[List[str]] = None,
) -> Dict[str, List[TaskMeasurement]]:
    containers = containers or ["E", "F"]
    tasks = generate_workload(
        n_tasks,
        seed=seed,
        repeat_band_pct=repeat_band_pct,
        include_memory_tasks=True,
    )
    results: Dict[str, List[TaskMeasurement]] = {"E": [], "F": []}
    runner_e = ContainerERunner() if "E" in containers else None
    runner_f = ContainerFRunner() if "F" in containers else None

    for task in tasks:
        if runner_e:
            row = runner_e.run(task)
            results["E"].append(row)
        if runner_f:
            row = runner_f.run(task)
            results["F"].append(row)

    return results


def aggregate(rows: List[TaskMeasurement]) -> dict:
    if not rows:
        return {}
    hop_totals: Dict[str, dict] = defaultdict(lambda: {"latency_ms": 0, "tokens_in": 0, "llm_calls": 0})
    for row in rows:
        for hop in row.hop_metrics or []:
            name = hop.get("hop") or "unknown"
            hop_totals[name]["latency_ms"] += int(hop.get("latency_ms") or 0)
            hop_totals[name]["tokens_in"] += int(hop.get("tokens_in") or 0)
            hop_totals[name]["llm_calls"] += int(hop.get("llm_calls") or 0)

    cache_hits = [r for r in rows if r.cache_hit is True]
    return {
        "n": len(rows),
        "avg_latency_ms": round(mean(r.latency_ms for r in rows), 1),
        "avg_tokens_in": round(mean(r.tokens_in for r in rows), 1),
        "avg_tokens_out": round(mean(r.tokens_out for r in rows), 1),
        "avg_cost_usd": round(mean(r.cost_usd for r in rows), 6),
        "avg_llm_calls": round(mean(r.llm_calls for r in rows), 2),
        "task_success_rate": round(sum(1 for r in rows if r.task_success) / len(rows), 3),
        "cache_hit_rate": round(len(cache_hits) / len(rows), 3) if rows else 0,
        "avg_embed_count": round(mean(r.embed_count or 0 for r in rows), 2),
        "avg_hop_latency_ms": {k: round(v["latency_ms"] / len(rows), 1) for k, v in hop_totals.items()},
        "avg_hop_tokens_in": {k: round(v["tokens_in"] / len(rows), 1) for k, v in hop_totals.items()},
    }


def aggregate_by_variant(rows: List[TaskMeasurement]) -> Dict[str, dict]:
    buckets: Dict[str, List[TaskMeasurement]] = defaultdict(list)
    for row in rows:
        buckets[row.variant].append(row)
    return {variant: aggregate(items) for variant, items in sorted(buckets.items())}


def format_report(results: Dict[str, List[TaskMeasurement]], *, repeat_band_pct: int) -> str:
    lines = [
        f"# Finance multi-agent E vs F (band {repeat_band_pct}%)",
        "",
        "Pipeline: researcher -> tool -> writer -> validator",
        "Same workload/tools/scoring as A/B (`benchmark/workload.py`).",
        "",
    ]
    for container in ("E", "F"):
        rows = results.get(container, [])
        if not rows:
            continue
        stats = aggregate(rows)
        lines.append(f"## Container {container} (n={len(rows)})")
        lines.append(
            f"- overall: latency={stats['avg_latency_ms']}ms tokens_in={stats['avg_tokens_in']} "
            f"llm_calls={stats['avg_llm_calls']} cost=${stats['avg_cost_usd']} "
            f"success={stats['task_success_rate']}"
        )
        if container == "F":
            lines.append(
                f"- cache_hit_rate={stats['cache_hit_rate']} embeds={stats['avg_embed_count']}"
            )
        lines.append("")
        by_variant = aggregate_by_variant(rows)
        for variant, vstats in by_variant.items():
            extra = f" cache_hit={vstats['cache_hit_rate']}" if container == "F" else ""
            lines.append(
                f"  - {variant}: latency={vstats['avg_latency_ms']}ms "
                f"tokens_in={vstats['avg_tokens_in']} success={vstats['task_success_rate']}{extra}"
            )
        lines.append("")
    return "\n".join(lines)


def write_jsonl(path: Path, rows: List[TaskMeasurement]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Finance multi-agent E vs F (same domain as A/B)")
    parser.add_argument("--tasks", type=int, default=60)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--band", type=int, default=40, choices=[20, 40, 60])
    parser.add_argument("--container", choices=["E", "F", "both"], default="both")
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark/results/h14_finance_multiagent"))
    args = parser.parse_args(argv)

    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key

        if not resolve_gemini_api_key():
            print("Error: GEMINI_API_KEY required.", file=sys.stderr)
            raise SystemExit(1)

    containers = ["E", "F"] if args.container == "both" else [args.container]
    print(f"Running finance multi-agent: {args.tasks} tasks, band={args.band}%, containers={containers}")
    results = run_finance_multiagent(
        args.tasks,
        seed=args.seed,
        repeat_band_pct=args.band,
        containers=containers,
    )

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = generate_workload(args.tasks, seed=args.seed, repeat_band_pct=args.band)
    meta = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "run_label": "H14_finance_multiagent",
        "n_tasks": args.tasks,
        "seed": args.seed,
        "repeat_band_pct": args.band,
        "containers": containers,
        "workload_stats": workload_stats(tasks),
        "aggregate": {c: aggregate(rows) for c, rows in results.items()},
        "by_variant": {c: aggregate_by_variant(rows) for c, rows in results.items()},
        "comparison_note": (
            "E = LangGraph multi-agent (growing context). "
            "F = ChorusGraph multi-agent (envelope handoffs + cache_gate + Cortex). "
            "Compare to A/B single-agent on same workload via run_volume.py."
        ),
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    for container, rows in results.items():
        write_jsonl(out_dir / f"container_{container.lower()}.jsonl", rows)
    print(format_report(results, repeat_band_pct=args.band))
    print(f"\nWrote results to {out_dir}")


if __name__ == "__main__":
    main()
