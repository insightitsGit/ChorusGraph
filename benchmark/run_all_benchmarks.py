"""Unified A/B/C/D/E/F benchmark — one scope, one report."""

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
from typing import Any, Dict, List, Optional

from benchmark.fl1.runner import FL1Runner
from benchmark.fc1.runner import FC1Runner
from benchmark.hl2.runner import HL2Runner
from benchmark.hc2.runner import HC2Runner
from benchmark.fl2.runner import FL2Runner
from benchmark.fc2.runner import FC2Runner
from benchmark.healthcare_workload import generate_healthcare_workload, workload_stats as hc_stats
from benchmark.measure import TaskMeasurement
from benchmark.multiagent_measure import MultiAgentMeasurement
from benchmark.run_finance_multiagent import aggregate as aggregate_finance_ma
from benchmark.run_finance_multiagent import aggregate_by_variant as aggregate_finance_by_variant
from benchmark.run_finance_multiagent import run_finance_multiagent
from benchmark.run_multiagent import aggregate_by_depth, run_multiagent_benchmark
from benchmark.workload import generate_workload, workload_stats


def run_single_agent(
    n_tasks: int,
    *,
    seed: int,
    repeat_band_pct: int,
) -> Dict[str, List[TaskMeasurement]]:
    tasks = generate_workload(n_tasks, seed=seed, repeat_band_pct=repeat_band_pct)
    runner_a = FL1Runner()
    runner_b = FC1Runner(seed_all_canonical_phrases=True)
    results: Dict[str, List[TaskMeasurement]] = {"A": [], "B": []}
    for task in tasks:
        row_a = runner_a.run(task)
        row_a.repeat_band_pct = repeat_band_pct
        results["A"].append(row_a)
        row_b = runner_b.run(task)
        row_b.repeat_band_pct = repeat_band_pct
        results["B"].append(row_b)
    return results


def aggregate_single(rows: List[TaskMeasurement]) -> dict:
    if not rows:
        return {}
    cache_hits = [r for r in rows if r.cache_hit is True]
    by_variant: Dict[str, List[TaskMeasurement]] = defaultdict(list)
    for row in rows:
        by_variant[row.variant].append(row)
    return {
        "n": len(rows),
        "avg_latency_ms": round(mean(r.latency_ms for r in rows), 1),
        "avg_tokens_in": round(mean(r.tokens_in for r in rows), 1),
        "avg_llm_calls": round(mean(r.llm_calls for r in rows), 2),
        "avg_cost_usd": round(mean(r.cost_usd for r in rows), 6),
        "task_success_rate": round(sum(1 for r in rows if r.task_success) / len(rows), 3),
        "cache_hit_rate": round(len(cache_hits) / len(rows), 3),
        "by_variant": {
            v: {
                "n": len(vrows),
                "avg_latency_ms": round(mean(r.latency_ms for r in vrows), 1),
                "avg_tokens_in": round(mean(r.tokens_in for r in vrows), 1),
                "task_success_rate": round(sum(1 for r in vrows if r.task_success) / len(vrows), 3),
                "cache_hit_rate": round(
                    sum(1 for r in vrows if r.cache_hit is True) / len(vrows), 3
                ),
            }
            for v, vrows in sorted(by_variant.items())
        },
    }


def aggregate_multiagent(rows: List[MultiAgentMeasurement]) -> dict:
    if not rows:
        return {}
    by_depth = aggregate_by_depth(rows)
    by_variant: Dict[str, List[MultiAgentMeasurement]] = defaultdict(list)
    for row in rows:
        # variant stored in case_id suffix or we need to pass - use pipeline for now
        by_variant["all"].append(row)
    return {
        "n": len(rows),
        "avg_latency_ms": round(mean(r.latency_ms for r in rows), 1),
        "avg_tokens_in": round(mean(r.tokens_in for r in rows), 1),
        "avg_llm_calls": round(mean(r.llm_calls for r in rows), 2),
        "task_success_rate": round(sum(1 for r in rows if r.task_success) / len(rows), 3),
        "abstain_rate": round(sum(1 for r in rows if r.abstained) / len(rows), 3),
        "avg_embed_count": round(mean(r.embed_count for r in rows), 2),
        "by_depth": by_depth,
    }


def format_unified_report(meta: dict) -> str:
    lines = [
        "# Unified benchmark A-F",
        "",
        f"Tasks/cases: {meta['n_tasks']} | seed: {meta['seed']} | repeat band: {meta['repeat_band_pct']}%",
        "",
        "## Single-agent finance (A vs B)",
        "",
    ]
    for c in ("A", "B"):
        s = meta["aggregate"]["single_agent"][c]
        lines.append(
            f"- **{c}**: latency={s['avg_latency_ms']}ms tokens_in={s['avg_tokens_in']} "
            f"llm_calls={s['avg_llm_calls']} success={s['task_success_rate']}"
            + (f" cache_hit={s['cache_hit_rate']}" if c == "B" else "")
        )
    lines.extend(["", "## Multi-agent healthcare (C vs D)", ""])
    for c in ("C", "D"):
        s = meta["aggregate"]["healthcare"][c]
        extra = f" embeds={s['avg_embed_count']}" if c == "D" else ""
        lines.append(
            f"- **{c}**: latency={s['avg_latency_ms']}ms tokens_in={s['avg_tokens_in']} "
            f"success={s['task_success_rate']} abstain={s['abstain_rate']}{extra}"
        )
    lines.extend(["", "## Multi-agent finance (E vs F)", ""])
    for c in ("E", "F"):
        s = meta["aggregate"]["finance_multiagent"][c]
        extra = f" cache_hit={s['cache_hit_rate']}" if c == "F" else ""
        lines.append(
            f"- **{c}**: latency={s['avg_latency_ms']}ms tokens_in={s['avg_tokens_in']} "
            f"llm_calls={s['avg_llm_calls']} success={s['task_success_rate']}{extra}"
        )
    lines.extend(["", "## Repeat variants (finance B vs F)", ""])
    for c, bucket in (("B", "single_agent"), ("F", "finance_multiagent")):
        agg = meta["aggregate"].get(bucket, {}).get(c, {})
        bv = agg.get("by_variant", {})
        for variant in ("exact_repeat", "paraphrase", "novel"):
            if variant not in bv:
                continue
            v = bv[variant]
            hit = f" cache={v.get('cache_hit_rate', 0)}"
            lines.append(
                f"- **{c} {variant}**: latency={v['avg_latency_ms']}ms tokens_in={v['avg_tokens_in']}{hit}"
            )
    return "\n".join(lines)


def write_jsonl(path: Path, rows: List[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            d = row.to_dict() if hasattr(row, "to_dict") else asdict(row)
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Run all containers A-F in one scope")
    parser.add_argument("--tasks", type=int, default=12, help="Tasks/cases per pair (default 12)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--band", type=int, default=40, choices=[20, 40, 60])
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark/results/h14_all_containers"))
    parser.add_argument("--skip", type=str, default="", help="Comma list to skip: A,B,C,D,E,F")
    args = parser.parse_args(argv)

    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key

        if not resolve_gemini_api_key():
            print("Error: GEMINI_API_KEY required.", file=sys.stderr)
            raise SystemExit(1)

    skip = {s.strip().upper() for s in args.skip.split(",") if s.strip()}
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Unified benchmark: n={args.tasks} seed={args.seed} band={args.band}% skip={skip or 'none'}")

    single: Dict[str, List[TaskMeasurement]] = {"A": [], "B": []}
    if "A" not in skip or "B" not in skip:
        print("Running single-agent A/B...")
        single = run_single_agent(args.tasks, seed=args.seed, repeat_band_pct=args.band)
        if "A" in skip:
            single["A"] = []
        if "B" in skip:
            single["B"] = []

    healthcare: Dict[str, List[MultiAgentMeasurement]] = {"C": [], "D": []}
    if "C" not in skip or "D" not in skip:
        print("Running healthcare multi-agent C/D...")
        hc = generate_healthcare_workload(args.tasks, seed=args.seed, repeat_band_pct=args.band)
        runner_c = HL2Runner() if "C" not in skip else None
        runner_d = HC2Runner() if "D" not in skip else None
        for case in hc:
            if runner_c:
                healthcare["C"].append(runner_c.run(case))
            if runner_d:
                healthcare["D"].append(runner_d.run(case))

    finance_ma: Dict[str, List[TaskMeasurement]] = {"E": [], "F": []}
    if "E" not in skip or "F" not in skip:
        print("Running finance multi-agent E/F...")
        containers = []
        if "E" not in skip:
            containers.append("E")
        if "F" not in skip:
            containers.append("F")
        finance_ma_raw = run_finance_multiagent(
            args.tasks, seed=args.seed, repeat_band_pct=args.band, containers=containers
        )
        finance_ma = {"E": finance_ma_raw.get("E", []), "F": finance_ma_raw.get("F", [])}

    meta = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "run_label": "H14_all_containers",
        "n_tasks": args.tasks,
        "seed": args.seed,
        "repeat_band_pct": args.band,
        "finance_workload_stats": workload_stats(
            generate_workload(args.tasks, seed=args.seed, repeat_band_pct=args.band)
        ),
        "healthcare_workload_stats": hc_stats(
            generate_healthcare_workload(args.tasks, seed=args.seed, repeat_band_pct=args.band)
        ),
        "aggregate": {
            "single_agent": {c: aggregate_single(rows) for c, rows in single.items() if rows},
            "healthcare": {c: aggregate_multiagent(rows) for c, rows in healthcare.items() if rows},
            "finance_multiagent": {
                c: aggregate_finance_ma(rows) for c, rows in finance_ma.items() if rows
            },
        },
        "finance_multiagent_by_variant": {
            c: aggregate_finance_by_variant(rows) for c, rows in finance_ma.items() if rows
        },
    }
    meta["aggregate"]["finance_multiagent"] = {
        c: {**meta["aggregate"]["finance_multiagent"][c], "by_variant": meta["finance_multiagent_by_variant"].get(c, {})}
        for c in meta["aggregate"]["finance_multiagent"]
    }

    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (out_dir / "REPORT.md").write_text(format_unified_report(meta), encoding="utf-8")

    if single["A"]:
        write_jsonl(out_dir / "container_a.jsonl", single["A"])
    if single["B"]:
        write_jsonl(out_dir / "container_b.jsonl", single["B"])
    if healthcare["C"]:
        write_jsonl(out_dir / "container_c.jsonl", healthcare["C"])
    if healthcare["D"]:
        write_jsonl(out_dir / "container_d.jsonl", healthcare["D"])
    if finance_ma["E"]:
        write_jsonl(out_dir / "container_e.jsonl", finance_ma["E"])
    if finance_ma["F"]:
        write_jsonl(out_dir / "container_f.jsonl", finance_ma["F"])

    print(format_unified_report(meta))
    print(f"\nWrote results to {out_dir}")


if __name__ == "__main__":
    main()
