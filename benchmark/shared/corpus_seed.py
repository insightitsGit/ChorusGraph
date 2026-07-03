"""Corpus-driven cache seeding — patterns from H9/H10/H11 benchmarks.

Past benchmark lessons (see benchmark/archive_results.py, run_volume.py):
- Finance FC1/FC2: after first successful tool run, seed message + all canonical phrases
  (``seed_all_canonical_phrases=True``). Use ``novel_only`` for held-out paraphrase tests.
- Healthcare HC2: after writer, seed presentation + paraphrases; paraphrase keys include
  ``[pipeline_depth=N]`` suffix (see hc2/cache_helpers.py).
- Workload: novel task must run before repeats in the same session so cache can warm.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Protocol, Sequence

from benchmark.finance.corpus import CANONICAL_QUERIES, COMPOUND_SCENARIOS
from benchmark.healthcare.cases import CASES, PARAPHRASES

SeedMode = Literal["all", "novel_only"]

# FX canonical_id → ISO pair for offline / warm-cache seeding.
CANONICAL_FX_PAIRS: Dict[str, tuple[str, str]] = {
    "usd_eur": ("USD", "EUR"),
    "usd_gbp": ("USD", "GBP"),
    "eur_gbp": ("EUR", "GBP"),
    "usd_jpy": ("USD", "JPY"),
    "usd_chf": ("USD", "CHF"),
    "usd_cad": ("USD", "CAD"),
    "eur_jpy": ("EUR", "JPY"),
}


class FinanceSeedRuntime(Protocol):
    cache: Any
    sidecar: Any
    session_tool_cache: Dict[str, Any]

    def seed_tool_cache(self, query_key: str, tool_result: Dict[str, Any], *, category_slug: str = ...) -> None: ...


class HealthcareSeedRuntime(Protocol):
    cache: Any
    sidecar: Any
    session_tool_cache: Dict[str, Any]


def finance_seed_mode(*, seed_all_canonical: bool) -> SeedMode:
    return "all" if seed_all_canonical else "novel_only"


def finance_seed_phrases(canonical_id: Optional[str], *, mode: SeedMode = "all") -> List[str]:
    """Phrases to seed after FX/compound tool success (H10 multi-phrase pattern)."""
    if not canonical_id or canonical_id.startswith("memory_"):
        return []
    phrases = list(CANONICAL_QUERIES.get(canonical_id, []))
    if not phrases:
        return []
    if mode == "novel_only":
        return [phrases[0]]
    return phrases


def finance_category_slug(canonical_id: Optional[str]) -> str:
    if canonical_id and canonical_id.startswith("compound_"):
        return "compound_savings"
    return "fx_rates"


def healthcare_base_case_id(case_id: str, *, canonical_id: str = "") -> str:
    if canonical_id:
        return canonical_id
    return case_id.split("-d")[0]


def healthcare_seed_phrases(
    *,
    case_id: str,
    presentation: str,
    canonical_id: str = "",
) -> List[str]:
    """Canonical presentation + paraphrases for a clinical case (HC2 pattern)."""
    base_id = healthcare_base_case_id(case_id, canonical_id=canonical_id)
    phrases: List[str] = []
    for row in CASES:
        if row["case_id"] == base_id:
            p = str(row["presentation"])
            if p and p not in phrases:
                phrases.append(p)
            break
    if not phrases and presentation:
        phrases.append(presentation)
    for alt in PARAPHRASES.get(base_id, []):
        if alt and alt not in phrases:
            phrases.append(alt)
    return phrases


def healthcare_cache_query_key(presentation: str, *, pipeline_depth: int) -> str:
    return f"{presentation}\n[pipeline_depth={pipeline_depth}]"


def healthcare_cache_query_keys(
    *,
    presentation: str,
    pipeline_depth: int,
    seed_phrases: Sequence[str],
) -> List[str]:
    """All query keys HC2 seeds — message, depth-suffixed paraphrases, plain paraphrases."""
    queries: List[str] = []
    primary = healthcare_cache_query_key(presentation, pipeline_depth=pipeline_depth)
    if primary:
        queries.append(primary)
    for phrase in seed_phrases:
        if not phrase:
            continue
        depth_key = healthcare_cache_query_key(phrase, pipeline_depth=pipeline_depth)
        if depth_key not in queries:
            queries.append(depth_key)
        if phrase not in queries:
            queries.append(phrase)
    return queries


def seed_finance_tool_cache(
    runtime: FinanceSeedRuntime,
    message: str,
    tool_result: Dict[str, Any],
    *,
    extra_queries: Optional[Sequence[str]] = None,
    category_slug: str = "fx_rates",
) -> None:
    """Seed semantic cache for message + extra queries (ReAct / FC2 tool hop)."""
    extra_queries = list(extra_queries or [])
    queries = [message] if message else []
    for phrase in extra_queries:
        if phrase and phrase not in queries:
            queries.append(phrase)
    for query_key in queries:
        if query_key:
            runtime.seed_tool_cache(query_key, tool_result, category_slug=category_slug)


def seed_healthcare_clinical_cache(
    runtime: HealthcareSeedRuntime,
    *,
    presentation: str,
    pipeline_depth: int,
    payload: Dict[str, Any],
    seed_phrases: Sequence[str],
    category_slug: str = "clinical_retrieval",
    session_id: Optional[str] = None,
) -> None:
    """Seed clinical pipeline facts (H21 — delegates to quality-gated helper)."""
    from benchmark.hc2.cache_helpers import seed_healthcare_cache

    seed_healthcare_cache(
        runtime,
        presentation,
        payload,
        extra_queries=list(seed_phrases),
        pipeline_depth=pipeline_depth,
        session_id=session_id,
    )


def warm_finance_corpus_cache(
    runtime: FinanceSeedRuntime,
    *,
    mode: SeedMode = "all",
    use_live_rates: bool = False,
) -> Dict[str, int]:
    """
    Pre-seed finance semantic cache from corpus (shadow-harness style, no LLM).

    Fetches one rate per FX canonical_id (live or stub) and seeds all phrases.
    Compound intents seeded from COMPOUND_SCENARIOS deterministic FV.
    """
    from chorusgraph.nodes.tool import compound_interest, fetch_exchange_rate

    stats = {"fx_pairs": 0, "compound_ids": 0, "queries_seeded": 0}

    for canonical_id, (from_c, to_c) in CANONICAL_FX_PAIRS.items():
        if use_live_rates:
            tool_result = fetch_exchange_rate(from_c, to_c)
        else:
            tool_result = {
                "from_currency": from_c,
                "to_currency": to_c,
                "rate": 1.0,
                "date": "stub",
                "source": "corpus_warm_stub",
            }
        phrases = finance_seed_phrases(canonical_id, mode=mode)
        if not phrases:
            continue
        seed_finance_tool_cache(
            runtime,
            phrases[0],
            tool_result,
            extra_queries=phrases,
            category_slug="fx_rates",
        )
        stats["fx_pairs"] += 1
        stats["queries_seeded"] += len(phrases)

    for canonical_id, params in COMPOUND_SCENARIOS.items():
        phrases = finance_seed_phrases(canonical_id, mode=mode)
        if not phrases:
            continue
        tool_result = compound_interest(
            principal=float(params["principal"]),
            annual_rate_pct=float(params["annual_rate_pct"]),
            years=float(params["years"]),
            compounds_per_year=int(params["compounds_per_year"]),
        )
        seed_finance_tool_cache(
            runtime,
            phrases[0],
            tool_result,
            extra_queries=phrases,
            category_slug="compound_savings",
        )
        stats["compound_ids"] += 1
        stats["queries_seeded"] += len(phrases)

    return stats
