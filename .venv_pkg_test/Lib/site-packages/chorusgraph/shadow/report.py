"""Aggregate shadow results into (h, FP) frontier."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from chorusgraph.shadow.results_store import ShadowRow

VERIFY_THRESHOLDS = (0.90, 0.93, 0.95, 0.97, 0.99)
FP_BUDGET = 0.01


@dataclass(frozen=True)
class FrontierPoint:
    slug: str
    verify_threshold: float
    hit_rate: float
    false_positive_rate: float
    n_queries: int
    n_would_serve: int
    n_fp: int


def _aggregate_rows(rows: Iterable[ShadowRow]) -> Tuple[float, float, int, int, int]:
    rows = list(rows)
    n = len(rows)
    if n == 0:
        return 0.0, 0.0, 0, 0, 0
    hits = [r for r in rows if r.is_hit]
    n_hit = len(hits)
    h = n_hit / n
    fp_eligible = [r for r in rows if r.fp_eligible]
    n_fp_elig = len(fp_eligible)
    fp_rows = [r for r in fp_eligible if r.verdict == "mismatch"]
    fp = (len(fp_rows) / n_fp_elig) if n_fp_elig else 0.0
    return h, fp, n, n_hit, len(fp_rows)


def frontier_table(rows: List[ShadowRow]) -> List[FrontierPoint]:
    by_key: dict[tuple[str, float], list[ShadowRow]] = defaultdict(list)
    for row in rows:
        by_key[(row.slug, row.verify_threshold)].append(row)

    points: list[FrontierPoint] = []
    for (slug, thresh), group in sorted(by_key.items()):
        h, fp, n, n_serve, n_fp = _aggregate_rows(group)
        points.append(
            FrontierPoint(
                slug=slug,
                verify_threshold=thresh,
                hit_rate=h,
                false_positive_rate=fp,
                n_queries=n,
                n_would_serve=n_serve,
                n_fp=n_fp,
            )
        )
    return points


def recommend_threshold(points: List[FrontierPoint]) -> Dict[str, float]:
    """Per slug: highest verify threshold with FP < budget."""
    by_slug: dict[str, list[FrontierPoint]] = defaultdict(list)
    for p in points:
        by_slug[p.slug].append(p)
    rec: dict[str, float] = {}
    for slug, slug_points in by_slug.items():
        eligible = [p for p in slug_points if p.false_positive_rate < FP_BUDGET]
        if eligible:
            rec[slug] = max(p.verify_threshold for p in eligible)
    return rec


def format_report(points: List[FrontierPoint]) -> str:
    lines = [
        "Shadow-mode (h, FP) frontier — LOCAL PROXY, not production traffic",
        "=" * 72,
        f"{'slug':<22} {'verify':>6} {'h':>8} {'FP':>8} {'hits':>6} {'fp_n':>5} {'n':>5}",
        "-" * 72,
    ]
    for p in points:
        lines.append(
            f"{p.slug:<22} {p.verify_threshold:>6.2f} {p.hit_rate:>8.3f} "
            f"{p.false_positive_rate:>8.3f} {p.n_would_serve:>6} {p.n_fp:>5} {p.n_queries:>5}"
        )
    lines.append("-" * 72)
    rec = recommend_threshold(points)
    if rec:
        lines.append("Recommended verify threshold (FP < 1%) per slug:")
        for slug, thresh in sorted(rec.items()):
            lines.append(f"  {slug}: {thresh:.2f}")
    else:
        lines.append("No slug met FP < 1% at any tested threshold.")
    return "\n".join(lines)
