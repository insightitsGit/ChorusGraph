"""Cold audit — sequential cache simulation with the real gate."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from chorusgraph.audit.ingest import LogRow
from chorusgraph.cache_gate import gate, seed_cache_entry
from chorusgraph.cache_gate.sidecar import SidecarStore
from chorusgraph.cache_gate.thresholds import measured_thresholds
from chorusgraph.policy.embedder_guard import build_guarded_cache
from chorusgraph.sections.models import CachePolicy, Section


@dataclass
class SimulatedQuery:
    query: str
    is_hit: bool
    coarse_score: float
    verify_score: float
    candidate_query: Optional[str] = None


@dataclass
class AuditResult:
    total_queries: int
    simulated_hits: int
    simulated_hit_rate: float
    queries: List[SimulatedQuery] = field(default_factory=list)
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    has_token_counts: bool = False
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    coarse_threshold: float = 0.0
    verify_threshold: float = 0.0
    category_slug: str = "general"

    @property
    def projected_cost_baseline_usd(self) -> Optional[float]:
        if not self.has_token_counts:
            return None
        return gemini_cost_usd(self.total_tokens_in, self.total_tokens_out)

    @property
    def projected_cost_with_cache_usd(self) -> Optional[float]:
        baseline = self.projected_cost_baseline_usd
        if baseline is None:
            return None
        saved = baseline * self.simulated_hit_rate
        return max(baseline - saved, 0.0)

    @property
    def projected_cost_savings_usd(self) -> Optional[float]:
        baseline = self.projected_cost_baseline_usd
        projected = self.projected_cost_with_cache_usd
        if baseline is None or projected is None:
            return None
        return baseline - projected


def gemini_cost_usd(tokens_in: int, tokens_out: int) -> float:
    """Gemini 2.5 Flash list pricing — same constants as benchmark runs."""
    from benchmark.shared.instrumented_gemini import _INPUT_USD_PER_M, _OUTPUT_USD_PER_M

    return (tokens_in * _INPUT_USD_PER_M + tokens_out * _OUTPUT_USD_PER_M) / 1_000_000


def run_cold_audit(
    rows: List[LogRow],
    *,
    tenant_id: str = "cold-audit",
    category_slug: str = "general",
    cache_policy: CachePolicy = CachePolicy.REPLAY_SAFE,
) -> AuditResult:
    """
    For each query in order, run the real two-stage gate against prior entries,
    then seed the in-memory PrismCache for subsequent queries.
    """
    thresholds = measured_thresholds()
    coarse = thresholds.coarse
    verify = thresholds.verify_for(category_slug)

    cache = build_guarded_cache(tenant_id)
    sidecar = SidecarStore(":memory:")
    now = time.time()

    simulated: list[SimulatedQuery] = []
    hits = 0
    total_tokens_in = 0
    total_tokens_out = 0
    has_tokens = False

    for offset, row in enumerate(rows):
        section = Section(
            section_id=f"audit-{offset}",
            category_slug=category_slug,
            content=row.query,
            cache_policy=cache_policy,
        )
        decision = gate(
            row.query,
            section,
            cache,
            sidecar,
            coarse_threshold=coarse,
            verify_threshold=verify,
            tenant_id=tenant_id,
            now=now + offset,
        )
        is_hit = decision.is_hit
        if is_hit:
            hits += 1
        simulated.append(
            SimulatedQuery(
                query=row.query,
                is_hit=is_hit,
                coarse_score=decision.coarse_score,
                verify_score=decision.verify_score,
                candidate_query=decision.candidate_query,
            )
        )

        seed_cache_entry(
            cache,
            sidecar,
            query=row.query,
            value={"response": f"seeded:{offset}"},
            category_slug=category_slug,
            cache_policy=cache_policy.value,
            now=now + offset,
        )

        if row.tokens_in is not None and row.tokens_out is not None:
            has_tokens = True
            total_tokens_in += row.tokens_in
            total_tokens_out += row.tokens_out

    timestamps = [r.timestamp for r in rows if r.timestamp is not None]
    total = len(rows)
    return AuditResult(
        total_queries=total,
        simulated_hits=hits,
        simulated_hit_rate=(hits / total) if total else 0.0,
        queries=simulated,
        date_range_start=min(timestamps) if timestamps else None,
        date_range_end=max(timestamps) if timestamps else None,
        has_token_counts=has_tokens,
        total_tokens_in=total_tokens_in,
        total_tokens_out=total_tokens_out,
        coarse_threshold=coarse,
        verify_threshold=verify,
        category_slug=category_slug,
    )


__all__ = ["AuditResult", "SimulatedQuery", "gemini_cost_usd", "run_cold_audit"]
