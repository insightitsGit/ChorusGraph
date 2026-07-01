"""Temporal-split production shadow replay."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Optional

from chorusgraph.cache_gate import gate, seed_cache_entry
from chorusgraph.cache_gate.sidecar import SidecarStore
from chorusgraph.policy.embedder_guard import build_guarded_cache
from chorusgraph.sections.models import CachePolicy, Section
from chorusgraph.shadow.report import VERIFY_THRESHOLDS
from chorusgraph.shadow.replay.ingest import load_jsonl
from chorusgraph.shadow.replay.policies import policy_for_slug
from chorusgraph.shadow.replay.schema import TurnRecord
from pathlib import Path

from chorusgraph.shadow.replay.stats import MIN_HITS


def temporal_split(
    records: List[TurnRecord],
    *,
    seed_fraction: float = 0.70,
) -> tuple[List[TurnRecord], List[TurnRecord]]:
    if not records:
        return [], []
    idx = max(1, int(len(records) * seed_fraction))
    if idx >= len(records):
        idx = len(records) - 1
    return records[:idx], records[idx:]


def _normalize_response(text: Any) -> str:
    if text is None:
        return ""
    s = str(text).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _responses_match(would: Any, actual: Any) -> bool:
    return _normalize_response(would) == _normalize_response(actual)


@dataclass
class ReplayRow:
    query: str
    slug: str
    cache_policy: str
    verify_threshold: float
    decision: str
    is_hit: bool
    fp_eligible: bool
    semantic_unscored: bool
    verdict: str
    coarse_score: float
    verify_score: float
    would_response: Optional[str] = None
    actual_response: Optional[str] = None


@dataclass
class ReplayResult:
    seed_count: int
    eval_count: int
    rows: List[ReplayRow] = field(default_factory=list)
    semantic_unscored_hits: int = 0


def run_temporal_replay(
    jsonl_path: Path | str,
    *,
    tenant_id: str = "website-hub-prod",
    seed_fraction: float = 0.70,
    coarse_threshold: float = 0.88,
    verify_thresholds: tuple[float, ...] = VERIFY_THRESHOLDS,
) -> ReplayResult:
    """
    Seed cache from earlier traffic; evaluate gate on later slice (shadow only).
    """
    records = load_jsonl(jsonl_path)
    seed_turns, eval_turns = temporal_split(records, seed_fraction=seed_fraction)

    cache = build_guarded_cache(tenant_id)
    sidecar = SidecarStore(":memory:")

    for turn in seed_turns:
        policy = policy_for_slug(turn.category_slug)
        if policy == CachePolicy.NO_CACHE:
            continue
        seed_cache_entry(
            cache,
            sidecar,
            query=turn.query,
            value=turn.response,
            category_slug=turn.category_slug,
            cache_policy=policy.value,
        )

    rows: list[ReplayRow] = []
    semantic_unscored = 0

    for turn in eval_turns:
        policy = policy_for_slug(turn.category_slug)
        section = Section(
            section_id=turn.section_id or "eval",
            category_slug=turn.category_slug,
            content=turn.query,
            cache_policy=policy,
        )
        for verify_threshold in verify_thresholds:
            decision = gate(
                turn.query,
                section,
                cache,
                sidecar,
                coarse_threshold=coarse_threshold,
                verify_threshold=verify_threshold,
            )
            semantic_unscored_hit = (
                decision.is_hit
                and policy == CachePolicy.SEMANTIC
            )
            if semantic_unscored_hit:
                semantic_unscored += 1

            if decision.counts_for_fp and decision.value is not None:
                match = _responses_match(decision.value, turn.response)
                verdict = "match" if match else "mismatch"
                would_resp = str(decision.value)
            elif semantic_unscored_hit:
                verdict = "semantic_unscored"
                would_resp = str(decision.value) if decision.value is not None else None
            elif decision.is_hit:
                verdict = "hit_ineligible"
                would_resp = str(decision.value) if decision.value is not None else None
            else:
                verdict = "miss"
                would_resp = None

            rows.append(
                ReplayRow(
                    query=turn.query,
                    slug=turn.category_slug,
                    cache_policy=policy.value,
                    verify_threshold=verify_threshold,
                    decision=decision.kind.value,
                    is_hit=decision.is_hit,
                    fp_eligible=decision.counts_for_fp,
                    semantic_unscored=semantic_unscored_hit,
                    verdict=verdict,
                    coarse_score=decision.coarse_score,
                    verify_score=decision.verify_score,
                    would_response=would_resp,
                    actual_response=str(turn.response),
                )
            )

    return ReplayResult(
        seed_count=len(seed_turns),
        eval_count=len(eval_turns),
        rows=rows,
        semantic_unscored_hits=semantic_unscored,
    )
