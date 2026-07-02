"""Realistic finance workload with documented repeat/paraphrase model."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

Variant = Literal["exact_repeat", "paraphrase", "novel"]

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

    while len(tasks) < n_tasks:
        session_id = f"session-{session_idx:03d}"
        session_canonical = canonical_ids[session_idx % len(canonical_ids)]
        phrases = CANONICAL_QUERIES[session_canonical]

        for pos in range(tasks_per_session):
            if len(tasks) >= n_tasks:
                break

            if pos == 0:
                variant: Variant = "novel"
                message = phrases[0]
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

            slug = "compound_savings" if session_canonical == "compound_savings" else "fx_rates"
            tasks.append(
                WorkloadTask(
                    task_id=f"task-{task_idx:04d}",
                    session_id=session_id,
                    message=message,
                    category_slug=slug,
                    variant=variant,
                    canonical_id=session_canonical,
                )
            )
            task_idx += 1

        session_idx += 1

    return tasks


def workload_stats(tasks: List[WorkloadTask]) -> Dict[str, int]:
    stats: Dict[str, int] = {"total": len(tasks), "sessions": len({t.session_id for t in tasks})}
    for variant in ("exact_repeat", "paraphrase", "novel"):
        stats[variant] = sum(1 for t in tasks if t.variant == variant)
    return stats
