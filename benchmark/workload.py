"""Realistic finance workload with documented repeat/paraphrase model."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

Variant = Literal[
    "exact_repeat",
    "paraphrase",
    "novel",
    "memory_seed",
    "memory_recall",
    "memory_recall_cross",
]

# Memory-bearing sessions — seed turn stores profile; recall turn exercises Cortex.
MEMORY_PROFILES: Dict[str, Dict[str, object]] = {
    "memory_risk_conservative": {
        "seed": (
            "I'm a conservative investor with low risk tolerance. "
            "I prefer stable USD-heavy portfolios and minimal FX speculation."
        ),
        "recalls": [
            "Given my stated risk tolerance, would increasing EUR exposure fit my profile?",
            "What risk profile did I tell you I prefer?",
        ],
        "expected_terms": ["conservative", "low", "usd"],
    },
    "memory_horizon_long": {
        "seed": (
            "I'm investing for a 20-year horizon and can tolerate short-term market volatility."
        ),
        "recalls": [
            "Based on my investment horizon, is a 3-year savings goal aligned with my plan?",
            "Remind me what time horizon I mentioned for my investments.",
        ],
        "expected_terms": ["20", "horizon", "long"],
    },
}

# Canonical FX query intents — each maps to fx_rates slug.
CANONICAL_QUERIES: Dict[str, List[str]] = {
    "usd_eur": [
        "What is the USD to EUR exchange rate today?",
        "USD/EUR rate please",
        "How many euros per US dollar right now?",
        "Current dollar to euro FX rate",
    ],
    "usd_gbp": [
        "What is the USD to GBP exchange rate today?",
        "USD/GBP rate please",
        "How many pounds sterling per dollar?",
        "Current USD to British pound exchange rate",
    ],
    "eur_gbp": [
        "What is the EUR to GBP exchange rate today?",
        "EUR/GBP rate please",
        "Euro to pound exchange rate now",
    ],
    "usd_jpy": [
        "What is the USD to JPY exchange rate today?",
        "USD/JPY rate please",
        "Dollar to yen FX rate",
    ],
    "compare_usd_eur_gbp": [
        "Compare USD to EUR and USD to GBP exchange rates — which is stronger against USD?",
        "USD/EUR vs USD/GBP — which currency is stronger versus the dollar?",
        "Give me both USD-EUR and USD-GBP rates and say which buys more per dollar.",
    ],
    "compound_savings": [
        "If I invest $10,000 at 5% annual interest compounded monthly for 3 years, what is the future value?",
        "Compound interest: $10000 principal, 5% APR, 3 years, monthly compounding.",
    ],
}

# Default repeat model weights (must sum to 1.0 for non-seed tasks).
REPEAT_MODEL = {
    "exact_repeat": 0.40,
    "paraphrase": 0.30,
    "novel": 0.30,
}

REPEAT_BANDS = {
    20: {"exact_repeat": 0.10, "paraphrase": 0.10, "novel": 0.80},
    40: {"exact_repeat": 0.40, "paraphrase": 0.30, "novel": 0.30},
    60: {"exact_repeat": 0.45, "paraphrase": 0.35, "novel": 0.20},
}


def repeat_model_for_band(band_pct: int) -> Dict[str, float]:
    """Map sensitivity band (20/40/60) to repeat/paraphrase/novel weights."""
    if band_pct not in REPEAT_BANDS:
        raise ValueError(f"repeat band must be one of {sorted(REPEAT_BANDS)}; got {band_pct}")
    return dict(REPEAT_BANDS[band_pct])

REPEAT_MODEL_DOC = """
Repeat/paraphrase model (defensible finance-chat pattern):
- 40% exact_repeat — user re-asks the same question in a session (common in chat UIs).
- 30% paraphrase — same intent/canonical_id, different wording (semantic cache target).
- 30% novel — first occurrence of a canonical intent in the session or one-off compound query.

Sessions group tasks so repeats/paraphrases occur AFTER a seed query warms tool/cache state.
Every Nth session (default 2) starts with memory_seed; the **next** session opens with
memory_recall_cross (Cortex group shared, empty chat history — B-only long-term recall).
Volume: scale n_tasks; full MIN_HITS=300 per slug needs ~750+ fx_rates tasks at 40% repeat
  across sessions (see estimate_min_tasks_for_slug).
""".strip()


@dataclass(frozen=True)
class WorkloadTask:
    task_id: str
    session_id: str
    message: str
    category_slug: str
    variant: Variant
    canonical_id: Optional[str] = None
    memory_cortex_group: Optional[str] = None
    cross_session_recall: bool = False


def estimate_min_tasks_for_slug(*, min_hits: int = 300, repeat_rate: float = 0.40) -> int:
    """Rough tasks needed if repeat_rate of queries hit the same slug after seeding."""
    if repeat_rate <= 0:
        return min_hits * len(CANONICAL_QUERIES)
    return int(min_hits / repeat_rate) + len(CANONICAL_QUERIES)


def generate_workload(
    n_tasks: int = 20,
    *,
    seed: int = 42,
    tasks_per_session: int = 5,
    repeat_band_pct: int = 40,
    include_memory_tasks: bool = True,
    memory_every_n_sessions: int = 2,
) -> List[WorkloadTask]:
    """
    Generate a volume-controllable finance query set.

    Each session starts with a novel seed, then mixes repeats and paraphrases
    so Container B's semantic cache can observe realistic hit patterns.
    """
    if n_tasks < 1:
        raise ValueError("n_tasks must be >= 1")

    repeat_model = repeat_model_for_band(repeat_band_pct)
    rng = random.Random(seed)
    canonical_ids = list(CANONICAL_QUERIES.keys())
    tasks: List[WorkloadTask] = []
    session_idx = 0
    task_idx = 0

    memory_ids = list(MEMORY_PROFILES.keys())
    pending_cross_recall: Optional[Dict[str, str]] = None

    while len(tasks) < n_tasks:
        session_id = f"session-{session_idx:03d}"
        session_canonical = canonical_ids[session_idx % len(canonical_ids)]
        phrases = CANONICAL_QUERIES[session_canonical]
        memory_session = (
            include_memory_tasks
            and memory_every_n_sessions > 0
            and session_idx % memory_every_n_sessions == 0
        )
        memory_profile_id = memory_ids[(session_idx // max(memory_every_n_sessions, 1)) % len(memory_ids)]
        memory_profile = MEMORY_PROFILES.get(memory_profile_id, {})
        cortex_group = f"profile-{memory_profile_id}-{(session_idx // max(memory_every_n_sessions, 1)):03d}"
        fx_pos = 0

        if pending_cross_recall and len(tasks) < n_tasks:
            recall_msg = pending_cross_recall["message"]
            tasks.append(
                WorkloadTask(
                    task_id=f"task-{task_idx:04d}",
                    session_id=session_id,
                    message=recall_msg,
                    category_slug="user_profile",
                    variant="memory_recall_cross",
                    canonical_id=pending_cross_recall["profile_id"],
                    memory_cortex_group=pending_cross_recall["cortex_group"],
                    cross_session_recall=True,
                )
            )
            task_idx += 1
            pending_cross_recall = None

        for pos in range(tasks_per_session):
            if len(tasks) >= n_tasks:
                break

            if memory_session and pos == 0:
                variant = "memory_seed"
                message = str(memory_profile.get("seed", ""))
                slug = "user_profile"
                canonical = memory_profile_id
                recalls = list(memory_profile.get("recalls") or [])
                pending_cross_recall = {
                    "profile_id": memory_profile_id,
                    "cortex_group": cortex_group,
                    "message": recalls[session_idx % len(recalls)] if recalls else "",
                }
                tasks.append(
                    WorkloadTask(
                        task_id=f"task-{task_idx:04d}",
                        session_id=session_id,
                        message=message,
                        category_slug=slug,
                        variant=variant,
                        canonical_id=canonical,
                        memory_cortex_group=cortex_group,
                    )
                )
                task_idx += 1
                continue

            if fx_pos == 0:
                variant = "novel"
                message = phrases[0]
                fx_pos += 1
            else:
                roll = rng.random()
                if roll < repeat_model["exact_repeat"]:
                    variant = "exact_repeat"
                    message = phrases[0]
                elif roll < repeat_model["exact_repeat"] + repeat_model["paraphrase"]:
                    variant = "paraphrase"
                    message = rng.choice(phrases[1:] or phrases)
                else:
                    variant = "novel"
                    other = rng.choice([c for c in canonical_ids if c != session_canonical])
                    message = CANONICAL_QUERIES[other][0]
                    session_canonical = other
                fx_pos += 1
            slug = "compound_savings" if session_canonical == "compound_savings" else "fx_rates"
            canonical = session_canonical
            mem_group = cortex_group if memory_session else None

            tasks.append(
                WorkloadTask(
                    task_id=f"task-{task_idx:04d}",
                    session_id=session_id,
                    message=message,
                    category_slug=slug,
                    variant=variant,
                    canonical_id=canonical,
                    memory_cortex_group=mem_group,
                )
            )
            task_idx += 1

        session_idx += 1

    return tasks


def workload_stats(tasks: List[WorkloadTask]) -> Dict[str, int]:
    stats: Dict[str, int] = {"total": len(tasks), "sessions": len({t.session_id for t in tasks})}
    for variant in (
        "exact_repeat",
        "paraphrase",
        "novel",
        "memory_seed",
        "memory_recall",
        "memory_recall_cross",
    ):
        stats[variant] = sum(1 for t in tasks if t.variant == variant)
    return stats
