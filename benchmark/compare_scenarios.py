"""Pairwise LangGraph vs ChorusGraph comparison within each scenario group."""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union

from benchmark.analyze import MetricCI, bootstrap_ci, proportion_ci, latency_percentile_ci
from benchmark.measure import TaskMeasurement
from benchmark.multiagent_measure import MultiAgentMeasurement
from benchmark.scenarios import SCENARIO_MATRIX, ScenarioId

RowLike = Union[TaskMeasurement, MultiAgentMeasurement, Dict[str, Any]]

# Comparison pairs: (LangGraph, ChorusGraph, group_key)
COMPARISON_PAIRS: Tuple[Tuple[ScenarioId, ScenarioId, str], ...] = (
    ("FL1", "FC1", "finance_single"),
    ("FL2", "FC2", "finance_multi"),
    ("HL1", "HC1", "healthcare_single"),
    ("HL2", "HC2", "healthcare_multi"),
)

Winner = Literal["langgraph", "chorusgraph", "tie", "inconclusive"]


@dataclass(frozen=True)
class ComparisonPair:
    langgraph: ScenarioId
    chorusgraph: ScenarioId
    group_key: str

    @property
    def label(self) -> str:
        return self.group_key.replace("_", " ").title()


def all_pairs() -> List[ComparisonPair]:
    return [
        ComparisonPair(langgraph=lg, chorusgraph=cg, group_key=key)
        for lg, cg, key in COMPARISON_PAIRS
    ]


@dataclass
class NormalizedRow:
    row_id: str
    scenario: str
    variant: str
    latency_ms: int
    llm_calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    task_success: bool
    tool_calls: int = 0
    cache_hit: Optional[bool] = None
    cache_score: Optional[float] = None
    embed_count: int = 0
    abstained: bool = False
    error: Optional[str] = None
    pipeline_depth: Optional[int] = None

    @property
    def valid(self) -> bool:
        if self.error:
            if "429" in self.error or "RESOURCE_EXHAUSTED" in self.error:
                return False
            return False
        return self.llm_calls > 0 or self.cache_hit or len(str(self.row_id)) > 0


def normalize_row(row: RowLike, *, scenario: str) -> NormalizedRow:
    if isinstance(row, dict):
        d = row
    else:
        d = asdict(row)
    row_id = str(d.get("task_id") or d.get("case_id") or "")
    return NormalizedRow(
        row_id=row_id,
        scenario=scenario,
        variant=str(d.get("variant") or "novel"),
        latency_ms=int(d.get("latency_ms") or 0),
        llm_calls=int(d.get("llm_calls") or 0),
        tokens_in=int(d.get("tokens_in") or 0),
        tokens_out=int(d.get("tokens_out") or 0),
        cost_usd=float(d.get("cost_usd") or 0.0),
        task_success=bool(d.get("task_success")),
        tool_calls=int(d.get("tool_calls") or 0),
        cache_hit=d.get("cache_hit"),
        cache_score=d.get("cache_score"),
        embed_count=int(d.get("embed_count") or 0),
        abstained=bool(d.get("abstained")),
        error=d.get("error"),
        pipeline_depth=d.get("pipeline_depth"),
    )


def _valid_rows(rows: Sequence[NormalizedRow]) -> List[NormalizedRow]:
    return [r for r in rows if r.valid]


def _side_metrics(rows: List[NormalizedRow]) -> Dict[str, MetricCI]:
    if not rows:
        return {}
    latencies = [r.latency_ms for r in rows]
    costs = [r.cost_usd for r in rows]
    successes = sum(1 for r in rows if r.task_success)
    errors = sum(1 for r in rows if r.error)
    cache_hits = sum(1 for r in rows if r.cache_hit)
    cache_hit_rows = [r for r in rows if r.cache_hit]
    llm_on_cache_hit = [r.llm_calls for r in cache_hit_rows]
    return {
        "latency_ms_p50": latency_percentile_ci(latencies, 0.50),
        "latency_ms_p95": latency_percentile_ci(latencies, 0.95),
        "latency_ms_mean": bootstrap_ci([float(x) for x in latencies], statistics.mean),
        "cost_usd_per_task": bootstrap_ci(costs, statistics.mean),
        "task_success_rate": proportion_ci(successes, len(rows)),
        "error_rate": proportion_ci(errors, len(rows)),
        "llm_calls_per_task": bootstrap_ci([float(r.llm_calls) for r in rows], statistics.mean),
        "tokens_in_per_task": bootstrap_ci([float(r.tokens_in) for r in rows], statistics.mean),
        "tokens_out_per_task": bootstrap_ci([float(r.tokens_out) for r in rows], statistics.mean),
        "tool_calls_per_task": bootstrap_ci([float(r.tool_calls) for r in rows], statistics.mean),
        "cache_hit_rate": proportion_ci(cache_hits, len(rows)),
        "llm_calls_on_cache_hit_mean": (
            bootstrap_ci([float(x) for x in llm_on_cache_hit], statistics.mean)
            if llm_on_cache_hit
            else MetricCI(0.0, 0.0, 0.0, 0, "none")
        ),
        "embed_count_per_task": bootstrap_ci([float(r.embed_count) for r in rows], statistics.mean),
        "abstain_rate": proportion_ci(sum(1 for r in rows if r.abstained), len(rows)),
    }


def _ci_dict(ci: MetricCI) -> Dict[str, Any]:
    return {
        "point": ci.point,
        "lower95": ci.lower95,
        "upper95": ci.upper95,
        "n": ci.n,
        "method": ci.method,
    }


def _winner(
    lang_ci: MetricCI,
    chorus_ci: MetricCI,
    *,
    lower_is_better: bool,
) -> Winner:
    if lang_ci.n == 0 or chorus_ci.n == 0:
        return "inconclusive"
    if lower_is_better:
        if chorus_ci.upper95 < lang_ci.lower95:
            return "chorusgraph"
        if lang_ci.upper95 < chorus_ci.lower95:
            return "langgraph"
    else:
        if chorus_ci.lower95 > lang_ci.upper95:
            return "chorusgraph"
        if lang_ci.lower95 > chorus_ci.upper95:
            return "langgraph"
    if abs(chorus_ci.point - lang_ci.point) < 1e-9:
        return "tie"
    # Marginal — point estimate favors one side but CIs overlap
    if lower_is_better:
        return "chorusgraph" if chorus_ci.point < lang_ci.point else "langgraph"
    return "chorusgraph" if chorus_ci.point > lang_ci.point else "langgraph"


@dataclass
class MetricComparison:
    metric: str
    langgraph: Dict[str, Any]
    chorusgraph: Dict[str, Any]
    delta_chorus_minus_lang: Optional[Dict[str, Any]]
    lower_is_better: bool
    winner: Winner
    unit: str = ""


METRIC_SPECS: Tuple[Tuple[str, bool, str], ...] = (
    ("task_success_rate", False, "rate"),
    ("llm_calls_per_task", True, "calls"),
    ("latency_ms_mean", True, "ms"),
    ("latency_ms_p50", True, "ms"),
    ("latency_ms_p95", True, "ms"),
    ("cost_usd_per_task", True, "USD"),
    ("cache_hit_rate", False, "rate"),
    ("llm_calls_on_cache_hit_mean", True, "calls"),
    ("tokens_in_per_task", True, "tokens"),
    ("tokens_out_per_task", True, "tokens"),
    ("tool_calls_per_task", True, "calls"),
    ("error_rate", True, "rate"),
    ("embed_count_per_task", True, "embeds"),
    ("abstain_rate", False, "rate"),
)


_KEY_METRICS = ("task_success_rate", "llm_calls_per_task", "latency_ms_mean", "cache_hit_rate", "abstain_rate")


def _compare_pair_core(
    lang_norm: List[NormalizedRow],
    chorus_norm: List[NormalizedRow],
    *,
    lang_id: str,
    chorus_id: str,
    group_key: str,
    lang_rows: Sequence[RowLike],
    chorus_rows: Sequence[RowLike],
    include_variants: bool,
) -> Dict[str, Any]:
    lang_metrics = _side_metrics(lang_norm)
    chorus_metrics = _side_metrics(chorus_norm)

    lang_by_id = {r.row_id: r for r in lang_norm}
    chorus_by_id = {r.row_id: r for r in chorus_norm}
    common_ids = sorted(set(lang_by_id) & set(chorus_by_id))

    paired_cost_delta = [
        chorus_by_id[i].cost_usd - lang_by_id[i].cost_usd for i in common_ids
    ]
    paired_latency_delta = [
        float(chorus_by_id[i].latency_ms - lang_by_id[i].latency_ms) for i in common_ids
    ]
    paired_llm_delta = [
        float(chorus_by_id[i].llm_calls - lang_by_id[i].llm_calls) for i in common_ids
    ]
    paired_success_delta = [
        float(int(chorus_by_id[i].task_success) - int(lang_by_id[i].task_success))
        for i in common_ids
    ]

    paired = {
        "n_paired": len(common_ids),
        "cost_delta_usd": _ci_dict(bootstrap_ci(paired_cost_delta, statistics.mean))
        if paired_cost_delta
        else None,
        "latency_delta_ms": _ci_dict(bootstrap_ci(paired_latency_delta, statistics.mean))
        if paired_latency_delta
        else None,
        "llm_calls_delta": _ci_dict(bootstrap_ci(paired_llm_delta, statistics.mean))
        if paired_llm_delta
        else None,
        "success_delta_rate": _ci_dict(bootstrap_ci(paired_success_delta, statistics.mean))
        if paired_success_delta
        else None,
    }

    metrics: List[Dict[str, Any]] = []
    chorus_wins = 0
    lang_wins = 0
    for name, lower_is_better, unit in METRIC_SPECS:
        l_ci = lang_metrics.get(name)
        c_ci = chorus_metrics.get(name)
        if l_ci is None or c_ci is None:
            continue
        if name == "cache_hit_rate" and c_ci.n == 0 and l_ci.point == 0:
            continue
        winner = _winner(l_ci, c_ci, lower_is_better=lower_is_better)
        if winner == "chorusgraph":
            chorus_wins += 1
        elif winner == "langgraph":
            lang_wins += 1
        delta_ci = None
        if name == "cost_usd_per_task" and paired_cost_delta:
            delta_ci = paired["cost_delta_usd"]
        elif name == "latency_ms_mean" and paired_latency_delta:
            delta_ci = paired["latency_delta_ms"]
        elif name == "llm_calls_per_task" and paired_llm_delta:
            delta_ci = paired["llm_calls_delta"]
        metrics.append(
            asdict(
                MetricComparison(
                    metric=name,
                    langgraph=_ci_dict(l_ci),
                    chorusgraph=_ci_dict(c_ci),
                    delta_chorus_minus_lang=delta_ci,
                    lower_is_better=lower_is_better,
                    winner=winner,
                    unit=unit,
                )
            )
        )

    overall_winner: Winner = "inconclusive"
    if chorus_wins > lang_wins:
        overall_winner = "chorusgraph"
    elif lang_wins > chorus_wins:
        overall_winner = "langgraph"
    elif chorus_wins == lang_wins and chorus_wins > 0:
        overall_winner = "tie"

    out: Dict[str, Any] = {
        "group": group_key,
        "langgraph": lang_id,
        "chorusgraph": chorus_id,
        "n_langgraph": len(lang_norm),
        "n_chorusgraph": len(chorus_norm),
        "paired": paired,
        "metrics": metrics,
        "scorecard": {
            "chorusgraph_wins": chorus_wins,
            "langgraph_wins": lang_wins,
            "overall_winner": overall_winner,
        },
    }

    if include_variants:
        by_variant: Dict[str, Any] = {}
        variants = sorted({r.variant for r in lang_norm + chorus_norm})
        for variant in variants:
            by_variant[variant] = compare_pair(
                [r for r in lang_rows if normalize_row(r, scenario=lang_id).variant == variant],
                [r for r in chorus_rows if normalize_row(r, scenario=chorus_id).variant == variant],
                lang_id=lang_id,
                chorus_id=chorus_id,
                group_key=f"{group_key}/{variant}",
                include_variants=False,
            )
        out["by_variant"] = by_variant

    return out


def compare_pair(
    lang_rows: Sequence[RowLike],
    chorus_rows: Sequence[RowLike],
    *,
    lang_id: str,
    chorus_id: str,
    group_key: str,
    include_variants: bool = True,
) -> Dict[str, Any]:
    lang_norm = _valid_rows([normalize_row(r, scenario=lang_id) for r in lang_rows])
    chorus_norm = _valid_rows([normalize_row(r, scenario=chorus_id) for r in chorus_rows])
    return _compare_pair_core(
        lang_norm,
        chorus_norm,
        lang_id=lang_id,
        chorus_id=chorus_id,
        group_key=group_key,
        lang_rows=lang_rows,
        chorus_rows=chorus_rows,
        include_variants=include_variants,
    )


def compare_all_groups(results: Dict[str, List[RowLike]]) -> Dict[str, Any]:
    groups: Dict[str, Any] = {}
    for pair in all_pairs():
        if pair.langgraph not in results or pair.chorusgraph not in results:
            continue
        if not results[pair.langgraph] and not results[pair.chorusgraph]:
            continue
        groups[pair.group_key] = compare_pair(
            results[pair.langgraph],
            results[pair.chorusgraph],
            lang_id=pair.langgraph,
            chorus_id=pair.chorusgraph,
            group_key=pair.group_key,
        )
    return {"groups": groups, "pairs": [asdict(p) for p in all_pairs()]}


def _fmt_ci(d: Optional[Dict[str, Any]], *, pct: bool = False) -> str:
    if not d or d.get("n", 0) == 0:
        return "—"
    point = d["point"]
    if pct:
        return f"{point * 100:.1f}% [{d['lower95'] * 100:.1f}%, {d['upper95'] * 100:.1f}%]"
    if point < 1 and "rate" not in str(d):
        return f"{point:.4f} [{d['lower95']:.4f}, {d['upper95']:.4f}]"
    return f"{point:.2f} [{d['lower95']:.2f}, {d['upper95']:.2f}]"


def _metric_label(name: str) -> str:
    labels = {
        "task_success_rate": "Task success",
        "llm_calls_per_task": "LLM calls / task",
        "latency_ms_mean": "Mean latency",
        "latency_ms_p50": "Latency p50",
        "latency_ms_p95": "Latency p95",
        "cost_usd_per_task": "Cost / task",
        "cache_hit_rate": "Cache hit rate",
        "llm_calls_on_cache_hit_mean": "LLM calls on cache hit",
        "tokens_in_per_task": "Tokens in / task",
        "tokens_out_per_task": "Tokens out / task",
        "tool_calls_per_task": "Tool calls / task",
        "error_rate": "Error rate",
        "embed_count_per_task": "Embeds / task",
        "abstain_rate": "Abstain rate",
    }
    return labels.get(name, name)


def _key_metrics_table(data: Dict[str, Any]) -> List[str]:
    """Compact table: success, LLM calls, latency, cache — honest read first."""
    by_name = {m["metric"]: m for m in data.get("metrics", [])}
    lines = [
        "| Metric | LangGraph | ChorusGraph | Δ (C−L) |",
        "|--------|-----------|-------------|---------|",
    ]
    for name in _KEY_METRICS:
        m = by_name.get(name)
        if not m:
            continue
        is_rate = "rate" in name
        delta = m.get("delta_chorus_minus_lang")
        delta_str = _fmt_ci(delta, pct=is_rate) if delta else "—"
        if is_rate and delta:
            delta_str = _fmt_ci(delta, pct=True)
        lines.append(
            f"| {_metric_label(name)} | {_fmt_ci(m['langgraph'], pct=is_rate)} | "
            f"{_fmt_ci(m['chorusgraph'], pct=is_rate)} | {delta_str} |"
        )
    return lines


def format_comparison_report(comparison: Dict[str, Any], *, cache_enabled: bool | None = None) -> str:
    lines = [
        "# LangGraph vs ChorusGraph — Group Comparisons",
        "",
        "Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.",
        "Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).",
        "",
    ]
    if cache_enabled is False:
        lines.extend(
            [
                "> **Honest mode:** semantic cache disabled (`--no-cache`). "
                "Expect **0% cache hits** on C scenarios — failures reflect full LLM/tool paths.",
                "",
            ]
        )
    for group_key, data in comparison.get("groups", {}).items():
        lg = data["langgraph"]
        cg = data["chorusgraph"]
        score = data["scorecard"]
        lines.append(f"## {group_key.replace('_', ' ').title()} ({lg} vs {cg})")
        lines.append("")
        lines.append(
            f"**Overall:** {score['overall_winner']} "
            f"(Chorus wins {score['chorusgraph_wins']} metrics, "
            f"LangGraph wins {score['langgraph_wins']} metrics)"
        )
        lines.append("")
        lines.append("### Key metrics")
        lines.append("")
        lines.extend(_key_metrics_table(data))
        lines.append("")
        lines.append("### All metrics")
        lines.append("")
        lines.append("| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |")
        lines.append("|--------|-----------|-------------|---------|--------|")
        for m in data.get("metrics", []):
            is_rate = "rate" in m["metric"]
            delta = m.get("delta_chorus_minus_lang")
            delta_str = _fmt_ci(delta, pct=False) if delta else "—"
            if is_rate and delta:
                delta_str = _fmt_ci(delta, pct=True)
            lines.append(
                f"| {_metric_label(m['metric'])} | {_fmt_ci(m['langgraph'], pct=is_rate)} | "
                f"{_fmt_ci(m['chorusgraph'], pct=is_rate)} | {delta_str} | **{m['winner']}** |"
            )
        paired = data.get("paired") or {}
        lines.append("")
        lines.append(f"Paired tasks: **{paired.get('n_paired', 0)}** (same task/case IDs)")
        lines.append("")
    return "\n".join(lines)


__all__ = [
    "COMPARISON_PAIRS",
    "ComparisonPair",
    "compare_all_groups",
    "compare_pair",
    "format_comparison_report",
    "normalize_row",
]
