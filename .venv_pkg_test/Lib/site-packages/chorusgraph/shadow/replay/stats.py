"""Statistical helpers for shadow replay reporting."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


MIN_HITS = 300
FP_BUDGET = 0.01
Z_95 = 1.959963984540054


class Verdict(str, Enum):
    CACHEABLE = "CACHEABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT DATA"
    UNSAFE = "UNSAFE"


@dataclass(frozen=True)
class RateEstimate:
    point: float
    upper95: float
    n: int
    successes: int


def wilson_upper(successes: int, n: int, z: float = Z_95) -> float:
    """Wilson score interval upper bound for binomial proportion (95%)."""
    if n <= 0:
        return 1.0
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p + z2 / (2.0 * n)
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n)
    return min(1.0, (centre + margin) / denom)


def clopper_pearson_upper(successes: int, n: int, alpha: float = 0.05) -> float:
    """Clopper-Pearson one-sided upper bound (95% default)."""
    if n <= 0:
        return 1.0
    try:
        from scipy.stats import beta as beta_dist

        return float(beta_dist.ppf(1.0 - alpha, successes + 1, n - successes))
    except ImportError:
        return wilson_upper(successes, n)


def fp_estimate(n_fp: int, n_would_serve: int) -> RateEstimate:
    upper = clopper_pearson_upper(n_fp, n_would_serve)
    point = (n_fp / n_would_serve) if n_would_serve else 0.0
    return RateEstimate(point=point, upper95=upper, n=n_would_serve, successes=n_fp)


def hit_rate_estimate(n_hit: int, n_total: int) -> float:
    return (n_hit / n_total) if n_total else 0.0


def classify_verdict(n_would_serve: int, fp_upper95: float) -> Verdict:
    if n_would_serve < MIN_HITS:
        return Verdict.INSUFFICIENT_DATA
    if fp_upper95 < FP_BUDGET:
        return Verdict.CACHEABLE
    return Verdict.UNSAFE
