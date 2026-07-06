"""Measured benchmark comparison points for cold-audit reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Canonical MVP scenario run — see benchmark/SCENARIOS.md and docs/BENCHMARK.md.
_DEFAULT_COMPARISON = (
    Path(__file__).resolve().parents[2]
    / "benchmark"
    / "results"
    / "mvp_scenarios"
    / "20260704_212111"
    / "comparison.json"
)


@dataclass(frozen=True)
class ScenarioBenchmark:
    label: str
    langgraph_llm_calls: float
    chorusgraph_llm_calls: float
    llm_reduction_pct: float
    langgraph_cost_usd: float
    chorusgraph_cost_usd: float
    cost_reduction_pct: float
    source: str


@dataclass(frozen=True)
class PortfolioBenchmark:
    """Equal-weight mean across all four canonical MVP scenarios."""

    run_id: str
    scenario_count: int
    mean_llm_reduction_pct: float
    mean_cost_reduction_pct: float
    finance_mean_llm_reduction_pct: float
    finance_mean_cost_reduction_pct: float
    healthcare_mean_llm_reduction_pct: float
    healthcare_mean_cost_reduction_pct: float
    source: str


def _cost_reduction_pct(lang: float, chorus: float) -> float:
    if lang <= 0:
        return 0.0
    return round((lang - chorus) / lang * 100.0, 1)


def _llm_reduction_pct(lang: float, chorus: float) -> float:
    if lang <= 0:
        return 0.0
    return round((lang - chorus) / lang * 100.0, 1)


def _metric_point(group: dict, metric: str, side: str) -> float:
    for entry in group.get("metrics", []):
        if entry.get("metric") == metric:
            return float(entry[side]["point"])
    raise KeyError(metric)


def load_scenario_benchmarks(path: Optional[Path] = None) -> List[ScenarioBenchmark]:
    comparison_path = path or _DEFAULT_COMPARISON
    if comparison_path.exists():
        data = json.loads(comparison_path.read_text(encoding="utf-8"))
        groups = data.get("groups", {})
        labels = {
            "finance_single": "Finance, single-agent (FL1->FC1)",
            "finance_multi": "Finance, multi-agent (FL2->FC2)",
            "healthcare_single": "Healthcare, single-agent (HL1->HC1)",
            "healthcare_multi": "Healthcare, multi-agent (HL2->HC2)",
        }
        out: list[ScenarioBenchmark] = []
        for key, label in labels.items():
            group = groups.get(key)
            if group is None:
                continue
            lang = _metric_point(group, "llm_calls_per_task", "langgraph")
            chorus = _metric_point(group, "llm_calls_per_task", "chorusgraph")
            lang_cost = _metric_point(group, "cost_usd_per_task", "langgraph")
            chorus_cost = _metric_point(group, "cost_usd_per_task", "chorusgraph")
            out.append(
                ScenarioBenchmark(
                    label=label,
                    langgraph_llm_calls=lang,
                    chorusgraph_llm_calls=chorus,
                    llm_reduction_pct=_llm_reduction_pct(lang, chorus),
                    langgraph_cost_usd=lang_cost,
                    chorusgraph_cost_usd=chorus_cost,
                    cost_reduction_pct=_cost_reduction_pct(lang_cost, chorus_cost),
                    source=str(comparison_path),
                )
            )
        if out:
            return out

    # Fallback — same canonical run values if comparison.json is absent (e.g. sdist).
    return [
        ScenarioBenchmark("Finance, single-agent (FL1->FC1)", 3.325, 0.925, 72.2, 0.000322, 0.000096, 70.2, "comparison.json finance_single"),
        ScenarioBenchmark("Finance, multi-agent (FL2->FC2)", 2.05, 0.825, 59.8, 0.000162, 0.000069, 57.5, "comparison.json finance_multi"),
        ScenarioBenchmark("Healthcare, single-agent (HL1->HC1)", 3.05, 1.975, 35.2, 0.000346, 0.000298, 14.0, "comparison.json healthcare_single"),
        ScenarioBenchmark("Healthcare, multi-agent (HL2->HC2)", 3.85, 3.475, 9.7, 0.000324, 0.000328, -1.3, "comparison.json healthcare_multi"),
    ]


def load_portfolio_benchmark(path: Optional[Path] = None) -> PortfolioBenchmark:
    """Equal-weight portfolio summary across the four canonical scenarios."""
    comparison_path = path or _DEFAULT_COMPARISON
    run_id = comparison_path.parent.name if comparison_path.exists() else "20260704_212111"
    scenarios = load_scenario_benchmarks(path)
    finance = [s for s in scenarios if s.label.startswith("Finance")]
    healthcare = [s for s in scenarios if s.label.startswith("Healthcare")]

    def _mean(vals: List[float]) -> float:
        return round(sum(vals) / len(vals), 1) if vals else 0.0

    return PortfolioBenchmark(
        run_id=run_id,
        scenario_count=len(scenarios),
        mean_llm_reduction_pct=_mean([s.llm_reduction_pct for s in scenarios]),
        mean_cost_reduction_pct=_mean([s.cost_reduction_pct for s in scenarios]),
        finance_mean_llm_reduction_pct=_mean([s.llm_reduction_pct for s in finance]),
        finance_mean_cost_reduction_pct=_mean([s.cost_reduction_pct for s in finance]),
        healthcare_mean_llm_reduction_pct=_mean([s.llm_reduction_pct for s in healthcare]),
        healthcare_mean_cost_reduction_pct=_mean([s.cost_reduction_pct for s in healthcare]),
        source=str(comparison_path),
    )


__all__ = ["PortfolioBenchmark", "ScenarioBenchmark", "load_portfolio_benchmark", "load_scenario_benchmarks"]
