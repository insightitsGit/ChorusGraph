"""Statistical analysis with confidence intervals — no point-estimate claims."""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from benchmark.measure import TaskMeasurement
from benchmark.workload import CANONICAL_QUERIES
from chorusgraph.shadow.replay.stats import MIN_HITS, Verdict, classify_verdict, wilson_upper


def is_valid_measurement(row: TaskMeasurement) -> bool:
    """Exclude quota/API failures from analysis CIs."""
    if row.error:
        if "429" in row.error or "RESOURCE_EXHAUSTED" in row.error:
            return False
        return False
    return row.llm_calls > 0 or row.cache_hit or len((row.answer or "").strip()) >= 10


def valid_rows(rows: List[TaskMeasurement]) -> List[TaskMeasurement]:
    return [r for r in rows if is_valid_measurement(r)]


@dataclass(frozen=True)
class MetricCI:
    point: float
    lower95: float
    upper95: float
    n: int
    method: str


def _percentile(sorted_vals: Sequence[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_vals[int(k)])
    return float(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f))


def bootstrap_ci(
    values: Sequence[float],
    stat_fn: Callable[[Sequence[float]], float],
    *,
    n_bootstrap: int = 2000,
    seed: int = 0,
) -> MetricCI:
    vals = list(values)
    n = len(vals)
    if n == 0:
        return MetricCI(0.0, 0.0, 0.0, 0, "bootstrap")
    rng = random.Random(seed)
    stats: List[float] = []
    for _ in range(n_bootstrap):
        sample = [vals[rng.randrange(n)] for _ in range(n)]
        stats.append(stat_fn(sample))
    stats.sort()
    point = stat_fn(vals)
    return MetricCI(
        point=point,
        lower95=_percentile(stats, 0.025),
        upper95=_percentile(stats, 0.975),
        n=n,
        method="bootstrap_2000",
    )


def proportion_ci(successes: int, n: int) -> MetricCI:
    point = (successes / n) if n else 0.0
    upper = wilson_upper(successes, n)
    lower = max(0.0, (2 * point - upper))  # symmetric Wilson approx for lower
    return MetricCI(point=point, lower95=lower, upper95=upper, n=n, method="wilson_95")


def latency_percentile_ci(latencies_ms: Sequence[int], percentile: float = 0.50) -> MetricCI:
    return bootstrap_ci(
        [float(x) for x in latencies_ms],
        lambda xs: _percentile(sorted(xs), percentile),
    )


def analyze_container(rows: List[TaskMeasurement]) -> Dict[str, MetricCI]:
    if not rows:
        return {}
    latencies = [r.latency_ms for r in rows]
    costs = [r.cost_usd for r in rows]
    successes = sum(1 for r in rows if r.task_success)
    return {
        "latency_ms_p50": latency_percentile_ci(latencies, 0.50),
        "latency_ms_p95": latency_percentile_ci(latencies, 0.95),
        "cost_per_task_usd": bootstrap_ci(costs, statistics.mean),
        "accuracy_rate": proportion_ci(successes, len(rows)),
        "llm_calls_per_task": bootstrap_ci([float(r.llm_calls) for r in rows], statistics.mean),
    }


def analyze_b_cache(rows: List[TaskMeasurement]) -> Dict[str, MetricCI]:
    hits = sum(1 for r in rows if r.cache_hit)
    return {"cache_hit_rate": proportion_ci(hits, len(rows)) if rows else MetricCI(0, 0, 0, 0, "wilson_95")}


def cache_fp_by_slug(rows: List[TaskMeasurement]) -> Dict[str, Dict[str, object]]:
    """Per-slug false-positive analysis from B cache hits."""
    by_slug: Dict[str, List[TaskMeasurement]] = {}
    for row in rows:
        slug = row.category_slug or "fx_rates"
        by_slug.setdefault(slug, []).append(row)

    out: Dict[str, Dict[str, object]] = {}
    for slug, slug_rows in by_slug.items():
        would_serve = [r for r in slug_rows if r.cache_hit]
        n_serve = len(would_serve)
        n_fp = sum(1 for r in would_serve if not r.task_success)
        fp_upper = wilson_upper(n_fp, n_serve) if n_serve else 1.0
        verdict = classify_verdict(n_serve, fp_upper)
        out[slug] = {
            "n_tasks": len(slug_rows),
            "n_would_serve": n_serve,
            "n_fp": n_fp,
            "fp_rate_point": (n_fp / n_serve) if n_serve else 0.0,
            "fp_upper95": fp_upper,
            "hit_rate_point": sum(1 for r in slug_rows if r.cache_hit) / len(slug_rows),
            "verdict": verdict.value,
            "cacheable": verdict == Verdict.CACHEABLE,
            "min_hits_required": MIN_HITS,
        }
    return out


def compare_ab(a_rows: List[TaskMeasurement], b_rows: List[TaskMeasurement], *, valid_only: bool = True) -> Dict[str, object]:
    """Delta metrics with bootstrap CI on paired cost/latency differences where task_ids align."""
    if valid_only:
        a_rows = valid_rows(a_rows)
        b_rows = valid_rows(b_rows)
    a_by_id = {r.task_id: r for r in a_rows}
    b_by_id = {r.task_id: r for r in b_rows}
    common = sorted(set(a_by_id) & set(b_by_id))
    cost_deltas = [b_by_id[t].cost_usd - a_by_id[t].cost_usd for t in common]
    lat_deltas = [float(b_by_id[t].latency_ms - a_by_id[t].latency_ms) for t in common]
    return {
        "n_paired": len(common),
        "n_valid_a": len(a_rows),
        "n_valid_b": len(b_rows),
        "cost_delta_usd_per_task": bootstrap_ci(cost_deltas, statistics.mean).__dict__ if cost_deltas else None,
        "latency_delta_ms": bootstrap_ci(lat_deltas, statistics.mean).__dict__ if lat_deltas else None,
        "container_a": {k: v.__dict__ for k, v in analyze_container(a_rows).items()},
        "container_b": {k: v.__dict__ for k, v in analyze_container(b_rows).items()},
        "b_cache": {k: v.__dict__ for k, v in analyze_b_cache(b_rows).items()},
        "b_cache_fp_by_slug": cache_fp_by_slug(b_rows),
    }


_MEMORY_VARIANTS = frozenset({"memory_seed", "memory_recall", "memory_recall_cross"})


def slice_rows(rows: List[TaskMeasurement], slice_name: str) -> List[TaskMeasurement]:
    if slice_name == "full":
        return list(rows)
    if slice_name == "fx_and_compound":
        return [r for r in rows if r.variant not in _MEMORY_VARIANTS]
    if slice_name == "fx_only":
        return [r for r in rows if (r.category_slug or "") == "fx_rates"]
    if slice_name == "memory_cross_session":
        return [r for r in rows if r.variant == "memory_recall_cross"]
    if slice_name == "memory_all":
        return [r for r in rows if r.variant in _MEMORY_VARIANTS or (r.category_slug or "") == "user_profile"]
    if slice_name == "cache_exact_repeat":
        return [r for r in rows if r.variant == "exact_repeat" and (r.category_slug or "") == "fx_rates"]
    if slice_name == "cache_paraphrase":
        return [r for r in rows if r.variant == "paraphrase" and (r.category_slug or "") == "fx_rates"]
    raise ValueError(f"unknown slice: {slice_name}")


SLICE_LABELS: Dict[str, str] = {
    "full": "Full workload (FX + compound + memory)",
    "fx_and_compound": "FX + compound only (excludes memory tasks)",
    "fx_only": "FX rate tasks only",
    "memory_cross_session": "Cross-session memory recall (empty chat history)",
    "memory_all": "All memory tasks",
    "cache_exact_repeat": "B cache — FX exact_repeat",
    "cache_paraphrase": "B cache — FX paraphrase",
}


def compare_ab_slices(
    a_rows: List[TaskMeasurement],
    b_rows: List[TaskMeasurement],
    *,
    slices: Optional[List[str]] = None,
) -> Dict[str, Dict[str, object]]:
    slices = slices or [
        "full",
        "fx_and_compound",
        "fx_only",
        "memory_cross_session",
        "memory_all",
    ]
    out: Dict[str, Dict[str, object]] = {}
    for name in slices:
        a_slice = slice_rows(a_rows, name)
        b_slice = slice_rows(b_rows, name)
        report: Dict[str, object] = {
            "label": SLICE_LABELS.get(name, name),
            "n_a": len(a_slice),
            "n_b": len(b_slice),
            "compare_ab": compare_ab(a_slice, b_slice),
        }
        if name in ("cache_exact_repeat", "cache_paraphrase"):
            report["compare_ab"] = compare_ab([], b_slice)
            report["b_cache_variant"] = {
                k: v.__dict__ for k, v in analyze_b_cache(b_slice).items()
            }
        out[name] = report
    return out


def held_out_paraphrase_forensics(
    b_rows: List[TaskMeasurement],
    *,
    seed_all_canonical_phrases: bool = True,
) -> Dict[str, object]:
    """
    H11: paraphrase queries disjoint from multi-phrase seed set.

    Meaningful only when B seeds the novel phrase (phrases[0]) but not all canonical variants.
    """
    paraphrase = slice_rows(b_rows, "cache_paraphrase")
    if seed_all_canonical_phrases:
        return {
            "n_held_out_paraphrase_fx": 0,
            "n_hit": 0,
            "n_miss": 0,
            "hit_rate_point": None,
            "note": "Run with --cache-seed-mode novel-only to measure semantic generalization.",
        }
    seed_phrases = {phrases[0] for phrases in CANONICAL_QUERIES.values() if phrases}
    held_out = [r for r in paraphrase if r.message not in seed_phrases]
    hits = [r for r in held_out if r.cache_hit]
    return {
        "n_held_out_paraphrase_fx": len(held_out),
        "n_hit": len(hits),
        "n_miss": len(held_out) - len(hits),
        "hit_rate_point": (len(hits) / len(held_out)) if held_out else 0.0,
        "note": "B seeded novel phrase only; paraphrase queries are disjoint from seed set.",
    }


def paraphrase_cache_forensics(b_rows: List[TaskMeasurement]) -> Dict[str, object]:
    """Verify/coarse score distribution for FX paraphrase cache decisions."""
    paraphrase = slice_rows(b_rows, "cache_paraphrase")
    hits = [r for r in paraphrase if r.cache_hit]
    misses = [r for r in paraphrase if r.cache_hit is False]
    verify_miss = [float(r.cache_verify_score) for r in misses if r.cache_verify_score is not None]
    coarse_miss = [float(r.cache_coarse_score) for r in misses if r.cache_coarse_score is not None]
    verify_hit = [float(r.cache_verify_score) for r in hits if r.cache_verify_score is not None]
    return {
        "n_paraphrase_fx": len(paraphrase),
        "n_hit": len(hits),
        "n_miss": len(misses),
        "hit_rate_point": (len(hits) / len(paraphrase)) if paraphrase else 0.0,
        "verify_score_miss_mean": statistics.mean(verify_miss) if verify_miss else None,
        "verify_score_miss_max": max(verify_miss) if verify_miss else None,
        "coarse_score_miss_mean": statistics.mean(coarse_miss) if coarse_miss else None,
        "verify_score_hit_mean": statistics.mean(verify_hit) if verify_hit else None,
        "exact_repeat_cache": compare_ab_slices([], b_rows, slices=["cache_exact_repeat"]).get(
            "cache_exact_repeat", {}
        ).get("b_cache_variant"),
    }


def format_slice_table(slices: Dict[str, Dict[str, object]]) -> str:
    lines = [
        "| Slice | n (A/B) | A accuracy (95% CI) | B accuracy (95% CI) | B cache hit-rate |",
        "|-------|---------|---------------------|---------------------|------------------|",
    ]
    for name, data in slices.items():
        if name.startswith("cache_"):
            b_cache = (data.get("b_cache_variant") or {}).get("cache_hit_rate") or {}
            n_b = data.get("n_b", 0)
            lines.append(
                f"| {SLICE_LABELS.get(name, name)} | —/{n_b} | — | — | "
                f"{b_cache.get('point', 0):.4f} [{b_cache.get('lower95', 0):.4f}, {b_cache.get('upper95', 0):.4f}] |"
            )
            continue
        ab = data.get("compare_ab") or {}
        a_acc = (ab.get("container_a") or {}).get("accuracy_rate") or {}
        b_acc = (ab.get("container_b") or {}).get("accuracy_rate") or {}
        b_cache = (ab.get("b_cache") or {}).get("cache_hit_rate") or {}
        n_a = data.get("n_a", 0)
        n_b = data.get("n_b", 0)
        cache_cell = (
            f"{b_cache.get('point', 0):.4f} [{b_cache.get('lower95', 0):.4f}, {b_cache.get('upper95', 0):.4f}]"
            if n_b and name != "memory_cross_session"
            else "—"
        )
        lines.append(
            f"| {SLICE_LABELS.get(name, name)} | {n_a}/{n_b} | "
            f"{a_acc.get('point', 0):.4f} [{a_acc.get('lower95', 0):.4f}, {a_acc.get('upper95', 0):.4f}] | "
            f"{b_acc.get('point', 0):.4f} [{b_acc.get('lower95', 0):.4f}, {b_acc.get('upper95', 0):.4f}] | "
            f"{cache_cell} |"
        )
    return "\n".join(lines)


def _fmt_ci(metric: dict, *, default: float = 0.0) -> str:
    point = metric.get("point", default)
    lo = metric.get("lower95", default)
    hi = metric.get("upper95", default)
    if not isinstance(point, (int, float)):
        return "—"
    return f"{float(point):.4f} [{float(lo):.4f}, {float(hi):.4f}]"


def format_ci_table(band_results: Dict[int, Dict[str, object]]) -> str:
    lines = ["| Band | Metric | A (95% CI) | B (95% CI) |", "|------|--------|------------|------------|"]
    for band, data in sorted(band_results.items()):
        ab = data.get("compare_ab") or {}
        for metric in ("latency_ms_p50", "cost_per_task_usd", "accuracy_rate"):
            a_m = (ab.get("container_a") or {}).get(metric) or {}
            b_m = (ab.get("container_b") or {}).get(metric) or {}
            lines.append(
                f"| {band}% | {metric} | {_fmt_ci(a_m)} | {_fmt_ci(b_m)} |"
            )
        cache = (ab.get("b_cache") or {}).get("cache_hit_rate") or {}
        lines.append(
            f"| {band}% | b_cache_hit_rate | — | {_fmt_ci(cache)} |"
        )
    return "\n".join(lines)
