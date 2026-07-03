"""Offline A/B rerun — stub Gemini when live quota exhausted (H9 post vector-fix)."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import List, Optional

from benchmark.fl1.runner import FL1Runner
from benchmark.fc1.runner import FC1Runner
from benchmark.measure import ComparisonReport
from benchmark.stub_gemini import StubGeminiClient
from benchmark.thresholds import THRESHOLD_PROVENANCE, measured_thresholds
from benchmark.workload import REPEAT_MODEL_DOC, generate_workload, workload_stats


def _patch_runner_a(runner: FL1Runner, stub: StubGeminiClient) -> None:
    from benchmark.fl1 import graph as a_graph

    runner.compiled, runner.gemini, runner._checkpointer = a_graph.build_langgraph_agent(gemini=stub)


def _patch_runner_b(runner: FC1Runner, stub: StubGeminiClient) -> None:
    runner._sessions.clear()
    runner._histories.clear()

    def _session_graph(session_id: str):
        if session_id not in runner._sessions:
            from chorusgraph.agents.policy import PlanPolicy
            from chorusgraph.examples.finance_agent.patterns_graph import TENANT_ID, build_react_graph, pattern_initial_state
            from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

            _ = pattern_initial_state
            runtime = FinanceRuntime(tenant_id=TENANT_ID, gemini=stub)
            compiled, rt = build_react_graph(
                runtime,
                policy=PlanPolicy(max_steps=6),
                coarse_threshold=runner._thresholds.coarse,
                verify_threshold=runner._thresholds.verify_for("fx_rates"),
            )
            runner._sessions[session_id] = (compiled, rt)
        return runner._sessions[session_id]

    runner._session_graph = _session_graph


def run_offline_benchmark(
    n_tasks: int = 30,
    *,
    seed: int = 42,
) -> ComparisonReport:
    tasks = generate_workload(n_tasks, seed=seed)
    report = ComparisonReport(workload_size=len(tasks))
    report.notes.append("MODE: offline stub Gemini (live API quota exhausted)")
    report.notes.append(f"Workload stats: {workload_stats(tasks)}")
    report.notes.append(f"Thresholds: coarse={measured_thresholds().coarse}, verify={measured_thresholds().verify_for('fx_rates')}")

    runner_a = FL1Runner()
    runner_b = FC1Runner()
    stub_a = StubGeminiClient()
    stub_b = StubGeminiClient()
    _patch_runner_a(runner_a, stub_a)
    _patch_runner_b(runner_b, stub_b)

    for task in tasks:
        report.container_a.append(runner_a.run(task))
        report.container_b.append(runner_b.run(task))

    return report


def _delta_summary(report: ComparisonReport) -> dict:
    a = report.container_a
    b = report.container_b
    if not a or not b:
        return {}
    a_calls = [r.llm_calls for r in a]
    b_calls = [r.llm_calls for r in b]
    a_lat = [r.latency_ms for r in a]
    b_lat = [r.latency_ms for r in b]
    return {
        "llm_calls_mean_a": round(statistics.mean(a_calls), 3),
        "llm_calls_mean_b": round(statistics.mean(b_calls), 3),
        "llm_calls_delta_b_minus_a": round(statistics.mean(b_calls) - statistics.mean(a_calls), 3),
        "latency_p50_a_ms": int(statistics.median(a_lat)),
        "latency_p50_b_ms": int(statistics.median(b_lat)),
        "task_success_a": round(sum(1 for r in a if r.task_success) / len(a), 4),
        "task_success_b": round(sum(1 for r in b if r.task_success) / len(b), 4),
        "b_cache_hit_rate": report.summary()["b_cache_hit_rate"],
    }


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Offline stub A/B (quota-safe)")
    parser.add_argument("--tasks", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("benchmark/results/h9_post_vector_fix/offline_ab.json"))
    args = parser.parse_args(argv)

    print(f"Offline stub A/B: {args.tasks} tasks")
    print(f"Repeat model:\n{REPEAT_MODEL_DOC}\n")
    print(f"Cache thresholds (B):\n{THRESHOLD_PROVENANCE}\n")

    report = run_offline_benchmark(args.tasks, seed=args.seed)
    payload = {
        "mode": "offline_stub_gemini",
        "summary": report.summary(),
        "delta": _delta_summary(report),
        "container_a": [r.to_dict() for r in report.container_a],
        "container_b": [r.to_dict() for r in report.container_b],
        "notes": report.notes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(report.format_report())
    print("\nDelta:", json.dumps(payload["delta"], indent=2))
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
