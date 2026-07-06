"""Format cold-audit reports (console, JSON, Markdown)."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from chorusgraph.audit.benchmark_reference import (
    PortfolioBenchmark,
    ScenarioBenchmark,
    load_portfolio_benchmark,
    load_scenario_benchmarks,
)
from chorusgraph.audit.simulate import AuditResult

DISCLAIMER = (
    "This is a text-similarity estimate on your historical logs — the Production Agent Pilot "
    "measures your *actual* cache hit rate and cost against your real production traffic over 14 days."
)


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _portfolio_dict(portfolio: PortfolioBenchmark) -> Dict[str, Any]:
    return {
        "run_id": portfolio.run_id,
        "scenario_count": portfolio.scenario_count,
        "mean_llm_call_reduction_pct": portfolio.mean_llm_reduction_pct,
        "mean_modeled_cost_reduction_pct": portfolio.mean_cost_reduction_pct,
        "finance_mean_llm_reduction_pct": portfolio.finance_mean_llm_reduction_pct,
        "finance_mean_cost_reduction_pct": portfolio.finance_mean_cost_reduction_pct,
        "healthcare_mean_llm_reduction_pct": portfolio.healthcare_mean_llm_reduction_pct,
        "healthcare_mean_cost_reduction_pct": portfolio.healthcare_mean_cost_reduction_pct,
        "note": (
            "Equal-weight mean across four canonical MVP scenarios (run "
            f"{portfolio.run_id}). Comparison point only — not a promise for your workload."
        ),
        "source": portfolio.source,
    }


def _format_portfolio_summary(portfolio: PortfolioBenchmark) -> str:
    return (
        f"Portfolio (4 scenarios, run {portfolio.run_id}): "
        f"~{portfolio.mean_llm_reduction_pct:.0f}% fewer LLM calls, "
        f"~{portfolio.mean_cost_reduction_pct:.0f}% lower modeled Gemini cost "
        f"(finance ~{portfolio.finance_mean_cost_reduction_pct:.0f}%, "
        f"healthcare ~{portfolio.healthcare_mean_cost_reduction_pct:.0f}%)"
    )


def audit_to_dict(result: AuditResult, benchmarks: List[ScenarioBenchmark] | None = None) -> Dict[str, Any]:
    benchmarks = benchmarks or load_scenario_benchmarks()
    payload: Dict[str, Any] = {
        "total_queries": result.total_queries,
        "simulated_hits": result.simulated_hits,
        "simulated_hit_rate": round(result.simulated_hit_rate, 4),
        "estimated_repeat_near_duplicate_rate": round(result.simulated_hit_rate, 4),
        "coarse_threshold": result.coarse_threshold,
        "verify_threshold": result.verify_threshold,
        "category_slug": result.category_slug,
        "date_range": {
            "start": result.date_range_start.isoformat() if result.date_range_start else None,
            "end": result.date_range_end.isoformat() if result.date_range_end else None,
        },
        "benchmark_llm_reduction_comparison": [
            {
                "scenario": b.label,
                "langgraph_llm_calls_per_task": b.langgraph_llm_calls,
                "chorusgraph_llm_calls_per_task": b.chorusgraph_llm_calls,
                "measured_llm_call_reduction_pct": b.llm_reduction_pct,
                "langgraph_cost_usd_per_task": b.langgraph_cost_usd,
                "chorusgraph_cost_usd_per_task": b.chorusgraph_cost_usd,
                "measured_cost_reduction_pct": b.cost_reduction_pct,
                "source": b.source,
            }
            for b in benchmarks
        ],
        "benchmark_portfolio_summary": _portfolio_dict(load_portfolio_benchmark()),
        "disclaimer": DISCLAIMER,
    }
    if result.has_token_counts:
        payload["token_cost_estimate"] = {
            "total_tokens_in": result.total_tokens_in,
            "total_tokens_out": result.total_tokens_out,
            "estimated_baseline_cost_usd": round(result.projected_cost_baseline_usd or 0.0, 6),
            "estimated_cost_with_simulated_cache_usd": round(
                result.projected_cost_with_cache_usd or 0.0, 6
            ),
            "estimated_cost_savings_usd": round(result.projected_cost_savings_usd or 0.0, 6),
            "note": (
                "Estimated from your log token counts and simulated hit rate; "
                "not measured production savings."
            ),
        }
    return payload


def format_console_report(result: AuditResult, *, log_path: str = "") -> str:
    benchmarks = load_scenario_benchmarks()
    lines = [
        "ChorusGraph Cold Audit (simulated from query text)",
        "=" * 56,
    ]
    if log_path:
        lines.append(f"Log: {log_path}")
    lines.append(f"Queries analyzed: {result.total_queries}")
    if result.date_range_start and result.date_range_end:
        lines.append(
            f"Date range: {result.date_range_start.date()} -> {result.date_range_end.date()}"
        )
    lines.append(
        f"Estimated repeat/near-duplicate rate (simulated): "
        f"{_pct(result.simulated_hit_rate)} ({result.simulated_hits}/{result.total_queries})"
    )
    lines.append(
        f"Gate thresholds: coarse={result.coarse_threshold:.2f}, "
        f"verify={result.verify_threshold:.2f} (category={result.category_slug})"
    )
    lines.append("")
    portfolio = load_portfolio_benchmark()
    lines.append("Benchmark overall (measured, equal-weight across 4 scenarios):")
    lines.append(f"  {_format_portfolio_summary(portfolio)}")
    lines.append("")
    lines.append("Per-scenario detail (not a promise for your log):")
    lines.append(
        f"{'Scenario':<44} {'L calls':>7} {'C calls':>7} {'LLM%':>6} {'cost%':>6}"
    )
    lines.append("-" * 74)
    for b in benchmarks:
        lines.append(
            f"{b.label:<44} {b.langgraph_llm_calls:>7.2f} {b.chorusgraph_llm_calls:>7.2f} "
            f"{b.llm_reduction_pct:>5.1f}% {b.cost_reduction_pct:>5.1f}%"
        )

    if result.has_token_counts:
        lines.append("")
        lines.append("Estimated cost from your log token counts (simulated):")
        lines.append(
            f"  Baseline (no cache): ${result.projected_cost_baseline_usd:.6f} "
            f"({result.total_tokens_in} in / {result.total_tokens_out} out tokens)"
        )
        lines.append(
            f"  With simulated cache: ${result.projected_cost_with_cache_usd:.6f} "
            f"(assumes {_pct(result.simulated_hit_rate)} of queries skip LLM cost)"
        )
        lines.append(f"  Estimated savings: ${result.projected_cost_savings_usd:.6f}")

    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def format_markdown_report(result: AuditResult, *, log_path: str = "") -> str:
    benchmarks = load_scenario_benchmarks()
    lines = [
        "# ChorusGraph Cold Audit",
        "",
        "_Simulated from your historical query text — not measured production traffic._",
        "",
    ]
    if log_path:
        lines.append(f"**Log:** `{log_path}`")
        lines.append("")
    lines.append(f"- **Queries analyzed:** {result.total_queries}")
    if result.date_range_start and result.date_range_end:
        lines.append(
            f"- **Date range:** {result.date_range_start.date()} -> {result.date_range_end.date()}"
        )
    lines.append(
        f"- **Estimated repeat/near-duplicate rate (simulated):** "
        f"{_pct(result.simulated_hit_rate)} ({result.simulated_hits}/{result.total_queries})"
    )
    lines.append(
        f"- **Gate thresholds:** coarse={result.coarse_threshold:.2f}, "
        f"verify={result.verify_threshold:.2f} (`{result.category_slug}`)"
    )
    lines.append("")
    portfolio = load_portfolio_benchmark()
    lines.append("## Benchmark overall (measured — not a promise for your workload)")
    lines.append("")
    lines.append(f"- {_format_portfolio_summary(portfolio)}")
    lines.append("")
    lines.append("## Per-scenario detail")
    lines.append("")
    lines.append("| Scenario | L LLM | C LLM | LLM reduction | Cost reduction |")
    lines.append("|----------|-------|-------|---------------|----------------|")
    for b in benchmarks:
        lines.append(
            f"| {b.label} | {b.langgraph_llm_calls:.2f} | {b.chorusgraph_llm_calls:.2f} | "
            f"{b.llm_reduction_pct:.1f}% | {b.cost_reduction_pct:.1f}% |"
        )
    if result.has_token_counts:
        lines.append("")
        lines.append("## Estimated cost from your token counts (simulated)")
        lines.append("")
        lines.append(
            f"- Baseline: **${result.projected_cost_baseline_usd:.6f}** "
            f"({result.total_tokens_in} tokens in, {result.total_tokens_out} tokens out)"
        )
        lines.append(
            f"- With simulated cache: **${result.projected_cost_with_cache_usd:.6f}**"
        )
        lines.append(f"- Estimated savings: **${result.projected_cost_savings_usd:.6f}**")
    lines.append("")
    lines.append(f"_{DISCLAIMER}_")
    return "\n".join(lines)


def format_json_report(result: AuditResult) -> str:
    return json.dumps(audit_to_dict(result), indent=2)


__all__ = [
    "DISCLAIMER",
    "audit_to_dict",
    "format_console_report",
    "format_json_report",
    "format_markdown_report",
]
