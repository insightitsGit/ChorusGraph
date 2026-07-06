"""Production shadow replay report with confidence bounds."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List

from chorusgraph.shadow.replay.replay import ReplayResult, ReplayRow
from chorusgraph.shadow.replay.stats import (
    MIN_HITS,
    Verdict,
    classify_verdict,
    fp_estimate,
    hit_rate_estimate,
)


@dataclass(frozen=True)
class SlugThresholdReport:
    slug: str
    verify_threshold: float
    h: float
    fp_point: float
    fp_upper95: float
    n_total: int
    n_would_serve: int
    n_fp: int
    verdict: Verdict


def build_slug_reports(result: ReplayResult) -> List[SlugThresholdReport]:
    by_key: dict[tuple[str, float], list[ReplayRow]] = defaultdict(list)
    for row in result.rows:
        by_key[(row.slug, row.verify_threshold)].append(row)

    reports: list[SlugThresholdReport] = []
    for (slug, thresh), group in sorted(by_key.items()):
        n_total = len(group)
        n_hit = sum(1 for r in group if r.is_hit)
        fp_rows = [r for r in group if r.fp_eligible]
        n_serve = len(fp_rows)
        n_fp = sum(1 for r in fp_rows if r.verdict == "mismatch")
        fp = fp_estimate(n_fp, n_serve)
        reports.append(
            SlugThresholdReport(
                slug=slug,
                verify_threshold=thresh,
                h=hit_rate_estimate(n_hit, n_total),
                fp_point=fp.point,
                fp_upper95=fp.upper95,
                n_total=n_total,
                n_would_serve=n_serve,
                n_fp=n_fp,
                verdict=classify_verdict(n_serve, fp.upper95),
            )
        )
    return reports


def format_production_report(
    result: ReplayResult,
    *,
    source: str,
) -> str:
    reports = build_slug_reports(result)
    semantic_rows = [r for r in result.rows if r.semantic_unscored]
    semantic_hits = len({(r.query, r.verify_threshold) for r in semantic_rows})

    lines = [
        f"Production shadow replay — {source}",
        f"seed_turns={result.seed_count} eval_turns={result.eval_count} "
        f"(temporal split; shadow only, never served)",
        f"MIN_HITS for CACHEABLE verdict: {MIN_HITS}",
        "=" * 96,
        f"{'slug':<14} {'verify':>6} {'h':>7} {'FP':>7} {'FP_up95':>8} "
        f"{'serve':>6} {'fp_n':>5} {'n':>5} {'verdict':<18}",
        "-" * 96,
    ]
    for r in reports:
        lines.append(
            f"{r.slug:<14} {r.verify_threshold:>6.2f} {r.h:>7.3f} {r.fp_point:>7.3f} "
            f"{r.fp_upper95:>8.3f} {r.n_would_serve:>6} {r.n_fp:>5} {r.n_total:>5} {r.verdict.value:<18}"
        )
    lines.append("-" * 96)

    cacheable = [r for r in reports if r.verdict == Verdict.CACHEABLE]
    if cacheable:
        lines.append("CACHEABLE slug/threshold pairs (FP_upper95 < 1%, n >= MIN_HITS):")
        for r in cacheable:
            lines.append(f"  {r.slug} @ verify={r.verify_threshold:.2f} h={r.h:.3f}")
    else:
        lines.append("No slug/threshold pair is CACHEABLE (insufficient n or FP bound too high).")

    lines.append("")
    lines.append(
        f"Semantic coverage gap: {semantic_hits} would-serve hits on SEMANTIC policy "
        f"(excluded from FP numerator; generative judge not run)."
    )
    if semantic_hits:
        lines.append("  → Generative LLM-judge handoff is RECOMMENDED before claiming semantic savings.")

    return "\n".join(lines)


def recommend_thresholds(reports: List[SlugThresholdReport]) -> Dict[str, float]:
    """Highest verify threshold per slug that is CACHEABLE."""
    by_slug: dict[str, list[SlugThresholdReport]] = defaultdict(list)
    for r in reports:
        by_slug[r.slug].append(r)
    rec: dict[str, float] = {}
    for slug, slug_reports in by_slug.items():
        eligible = [r for r in slug_reports if r.verdict == Verdict.CACHEABLE]
        if eligible:
            rec[slug] = max(r.verify_threshold for r in eligible)
    return rec
