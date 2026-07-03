"""Healthcare benchmark workload — clinical cases + pipeline depth sweep."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Literal, Optional

from benchmark.healthcare.cases import CASES, PARAPHRASES, corpus_stats as healthcare_corpus_stats

PipelineDepth = Literal[2, 4, 6]
HealthcareVariant = Literal["novel", "exact_repeat", "paraphrase"]

REPEAT_BANDS = {
    20: {"exact_repeat": 0.10, "paraphrase": 0.10, "novel": 0.80},
    40: {"exact_repeat": 0.40, "paraphrase": 0.30, "novel": 0.30},
    60: {"exact_repeat": 0.45, "paraphrase": 0.35, "novel": 0.20},
}

__all__ = [
    "CASES",
    "PARAPHRASES",
    "HealthcareCase",
    "PIPELINE_AGENTS",
    "REPEAT_BANDS",
    "generate_healthcare_workload",
    "healthcare_corpus_stats",
    "repeat_model_for_band",
    "workload_stats",
]


@dataclass(frozen=True)
class HealthcareCase:
    case_id: str
    presentation: str
    expected_abstain: bool
    must_cite: List[str]
    drugs: List[str]
    topic: str
    pipeline_depth: PipelineDepth
    variant: HealthcareVariant = "novel"
    session_id: str = "session-000"
    canonical_id: str = ""


def repeat_model_for_band(band_pct: int) -> dict[str, float]:
    if band_pct not in REPEAT_BANDS:
        raise ValueError(f"repeat band must be one of {sorted(REPEAT_BANDS)}; got {band_pct}")
    return dict(REPEAT_BANDS[band_pct])


def generate_healthcare_workload(
    n_cases: int = 10,
    *,
    seed: int = 42,
    depths: Optional[List[PipelineDepth]] = None,
    repeat_band_pct: int = 40,
) -> List[HealthcareCase]:
    depths = depths or [2, 4, 6]
    rng = random.Random(seed)
    repeat_model = repeat_model_for_band(repeat_band_pct)
    pool = list(CASES)
    tasks: List[HealthcareCase] = []
    session_idx = 0
    case_idx = 0
    pos_in_session = 0

    while len(tasks) < n_cases:
        if pos_in_session == 0:
            session_idx += 1
            pos_in_session = 0

        base = dict(pool[(session_idx - 1) % len(pool)])
        depth = depths[case_idx % len(depths)]
        canonical = str(base["case_id"])
        presentation = str(base["presentation"])
        variant: HealthcareVariant = "novel"

        if pos_in_session > 0:
            roll = rng.random()
            if roll < repeat_model["exact_repeat"]:
                variant = "exact_repeat"
                presentation = str(base["presentation"])
            elif roll < repeat_model["exact_repeat"] + repeat_model["paraphrase"]:
                variant = "paraphrase"
                alts = PARAPHRASES.get(canonical, [])
                presentation = rng.choice(alts) if alts else str(base["presentation"])
            else:
                variant = "novel"
                other = pool[(session_idx + case_idx) % len(pool)]
                base = dict(other)
                canonical = str(base["case_id"])
                presentation = str(base["presentation"])

        tasks.append(
            HealthcareCase(
                case_id=f"{base['case_id']}-d{depth}-{case_idx:02d}",
                presentation=presentation,
                expected_abstain=bool(base["expected_abstain"]),
                must_cite=list(base["must_cite"]),
                drugs=list(base["drugs"]),
                topic=base["topic"],
                pipeline_depth=depth,
                variant=variant,
                session_id=f"hc-session-{session_idx:03d}",
                canonical_id=canonical,
            )
        )
        case_idx += 1
        pos_in_session += 1
        if pos_in_session >= 3:
            pos_in_session = 0

    # Novel cases must run before repeats in the same session so cache can warm up.
    def _variant_order(case: HealthcareCase) -> tuple[int, int]:
        order = {"novel": 0, "paraphrase": 1, "exact_repeat": 2}
        return (order.get(case.variant, 0), case.pipeline_depth)

    tasks.sort(key=lambda c: (c.session_id, _variant_order(c)))
    return tasks


def workload_stats(cases: List[HealthcareCase]) -> dict[str, int]:
    stats: dict[str, int] = {"total": len(cases), "sessions": len({c.session_id for c in cases})}
    for variant in ("exact_repeat", "paraphrase", "novel"):
        stats[variant] = sum(1 for c in cases if c.variant == variant)
    for depth in (2, 4, 6):
        stats[f"depth_{depth}"] = sum(1 for c in cases if c.pipeline_depth == depth)
    return stats


PIPELINE_AGENTS: dict[int, List[str]] = {
    2: ["intake", "writer"],
    4: ["intake", "retrieve", "analyze", "writer"],
    6: ["intake", "retrieve", "analyze", "drug_check", "safety", "writer"],
}
