"""Finance benchmark corpus — FX pairs, compound scenarios, memory profiles."""

from __future__ import annotations

from typing import Dict, List

# Topic tags for coverage reporting (not used at runtime).
TOPIC_TAGS: Dict[str, str] = {
    "usd_eur": "fx_major",
    "usd_gbp": "fx_major",
    "eur_gbp": "fx_cross",
    "usd_jpy": "fx_major",
    "usd_chf": "fx_major",
    "usd_cad": "fx_major",
    "eur_jpy": "fx_cross",
    "compare_usd_eur_gbp": "fx_compare",
    "compound_savings": "compound",
    "compound_retirement": "compound",
    "compound_loan": "compound",
    "memory_risk_conservative": "memory",
    "memory_horizon_long": "memory",
    "memory_goal_house": "memory",
    "memory_currency_eur": "memory",
    "memory_income_fixed": "memory",
}

# Memory-bearing sessions — seed turn stores profile; recall exercises Cortex.
MEMORY_PROFILES: Dict[str, Dict[str, object]] = {
    "memory_risk_conservative": {
        "seed": (
            "I'm a conservative investor with low risk tolerance. "
            "I prefer stable USD-heavy portfolios and minimal FX speculation."
        ),
        "recalls": [
            "Given my stated risk tolerance, would increasing EUR exposure fit my profile?",
            "What risk profile did I tell you I prefer?",
            "Should I add emerging-market FX given what you know about my preferences?",
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
            "Would a 6-month CD ladder match the timeline I shared earlier?",
        ],
        "expected_terms": ["20", "horizon", "long"],
    },
    "memory_goal_house": {
        "seed": (
            "I'm saving for a house down payment in 4 years. "
            "I want to preserve capital and avoid high-volatility assets."
        ),
        "recalls": [
            "Given my house down-payment goal, is a 90% equity portfolio appropriate?",
            "What savings goal and timeline did I mention?",
            "Should I prioritize liquidity for the timeline I described?",
        ],
        "expected_terms": ["house", "down", "4"],
    },
    "memory_currency_eur": {
        "seed": (
            "I receive monthly income in EUR but pay most expenses in USD. "
            "I want to minimize conversion costs when rates move."
        ),
        "recalls": [
            "Which currencies did I say my income and expenses are in?",
            "Should I hedge EUR exposure given my income/expense mix?",
            "Remind me of my currency mismatch situation.",
        ],
        "expected_terms": ["eur", "usd", "income"],
    },
    "memory_income_fixed": {
        "seed": (
            "I'm retired on a fixed pension with no wage income. "
            "Capital preservation is more important than aggressive growth."
        ),
        "recalls": [
            "Given my fixed pension, is a leveraged FX strategy suitable?",
            "What did I say about my income situation and risk priority?",
            "Would high-yield speculative assets fit the profile I described?",
        ],
        "expected_terms": ["pension", "fixed", "preserv"],
    },
}

# Canonical FX and compound query intents — each maps to a category_slug.
CANONICAL_QUERIES: Dict[str, List[str]] = {
    "usd_eur": [
        "What is the USD to EUR exchange rate today?",
        "USD/EUR rate please",
        "How many euros per US dollar right now?",
        "Current dollar to euro FX rate",
        "Live USD-EUR conversion rate for a wire transfer",
    ],
    "usd_gbp": [
        "What is the USD to GBP exchange rate today?",
        "USD/GBP rate please",
        "How many pounds sterling per dollar?",
        "Current USD to British pound exchange rate",
        "Dollar to pound FX quote for today",
    ],
    "eur_gbp": [
        "What is the EUR to GBP exchange rate today?",
        "EUR/GBP rate please",
        "Euro to pound exchange rate now",
        "How many GBP per euro at current market?",
    ],
    "usd_jpy": [
        "What is the USD to JPY exchange rate today?",
        "USD/JPY rate please",
        "Dollar to yen FX rate",
        "Current USD/JPY spot rate",
    ],
    "usd_chf": [
        "What is the USD to CHF exchange rate today?",
        "USD/CHF rate please",
        "How many Swiss francs per US dollar?",
        "Current dollar to franc FX rate",
    ],
    "usd_cad": [
        "What is the USD to CAD exchange rate today?",
        "USD/CAD rate please",
        "US dollar to Canadian dollar exchange rate",
        "Live USD-CAD rate for cross-border payment",
    ],
    "eur_jpy": [
        "What is the EUR to JPY exchange rate today?",
        "EUR/JPY rate please",
        "Euro to yen exchange rate now",
        "How many yen per euro today?",
    ],
    "compare_usd_eur_gbp": [
        "Compare USD to EUR and USD to GBP exchange rates — which is stronger against USD?",
        "USD/EUR vs USD/GBP — which currency is stronger versus the dollar?",
        "Give me both USD-EUR and USD-GBP rates and say which buys more per dollar.",
        "I need USD/EUR and USD/GBP side by side — which pair is stronger for USD?",
    ],
    "compound_savings": [
        "If I invest $10,000 at 5% annual interest compounded monthly for 3 years, what is the future value?",
        "Compound interest: $10000 principal, 5% APR, 3 years, monthly compounding.",
        "Future value of $10k at 5% compounded monthly over 3 years?",
    ],
    "compound_retirement": [
        "If I invest $50,000 at 6% annual interest compounded quarterly for 10 years, what is the future value?",
        "Retirement nest egg: $50000 principal, 6% APR, 10 years, quarterly compounding — FV?",
        "Compound $50k at 6% for 10 years with quarterly compounding — total amount?",
    ],
    "compound_loan": [
        "If I invest $25,000 at 4.5% annual interest compounded daily for 5 years, what is the future value?",
        "Savings growth: $25000 at 4.5% APR, 5 years, daily compounding — future value?",
        "What is the FV of $25k invested at 4.5% compounded daily for 5 years?",
    ],
}

# Named compound scenarios with expected parameters (for docs / dry-run validation).
COMPOUND_SCENARIOS: Dict[str, Dict[str, object]] = {
    "compound_savings": {
        "principal": 10_000,
        "annual_rate_pct": 5.0,
        "years": 3.0,
        "compounds_per_year": 12,
    },
    "compound_retirement": {
        "principal": 50_000,
        "annual_rate_pct": 6.0,
        "years": 10.0,
        "compounds_per_year": 4,
    },
    "compound_loan": {
        "principal": 25_000,
        "annual_rate_pct": 4.5,
        "years": 5.0,
        "compounds_per_year": 365,
    },
}


def corpus_stats() -> Dict[str, int]:
    """Summary counts for tests and benchmark reports."""
    fx = sum(1 for k in CANONICAL_QUERIES if k.startswith(("usd_", "eur_", "compare_")))
    compound = sum(1 for k in CANONICAL_QUERIES if k.startswith("compound_"))
    phrases = sum(len(v) for v in CANONICAL_QUERIES.values())
    return {
        "fx_canonical_ids": fx,
        "compound_canonical_ids": compound,
        "total_canonical_ids": len(CANONICAL_QUERIES),
        "total_phrases": phrases,
        "memory_profiles": len(MEMORY_PROFILES),
        "topics": len(set(TOPIC_TAGS.values())),
    }
