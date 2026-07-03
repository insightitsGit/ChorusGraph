"""Tests for corpus-driven cache seeding (H9/H10 patterns)."""

from __future__ import annotations

from benchmark.finance.corpus import CANONICAL_QUERIES
from benchmark.healthcare_workload import HealthcareCase
from benchmark.shared.corpus_seed import (
    finance_seed_phrases,
    healthcare_cache_query_keys,
    healthcare_seed_phrases,
    warm_finance_corpus_cache,
)
from chorusgraph.cache_gate import gate
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime
from chorusgraph.sections.models import CachePolicy, Section


def test_finance_seed_all_vs_novel_only():
    phrases = CANONICAL_QUERIES["usd_eur"]
    assert finance_seed_phrases("usd_eur", mode="all") == phrases
    assert finance_seed_phrases("usd_eur", mode="novel_only") == [phrases[0]]
    assert finance_seed_phrases("memory_risk_conservative") == []


def test_healthcare_seed_phrases_cover_paraphrases():
    phrases = healthcare_seed_phrases(
        case_id="case-001-d2-00",
        presentation="68yo with AF on warfarin...",
        canonical_id="case-001",
    )
    assert len(phrases) >= 4
    assert any("warfarin" in p for p in phrases)


def test_healthcare_cache_query_keys_include_depth():
    keys = healthcare_cache_query_keys(
        presentation="BP 142/92",
        pipeline_depth=6,
        seed_phrases=["Stage 1 hypertension with 12% risk"],
    )
    assert any("[pipeline_depth=6]" in k for k in keys)
    assert "Stage 1 hypertension with 12% risk" in keys


def test_warm_finance_corpus_cache_enables_paraphrase_hit():
    runtime = FinanceRuntime(tenant_id="test-warm-corpus")
    stats = warm_finance_corpus_cache(runtime, mode="all", use_live_rates=False)
    assert stats["fx_pairs"] >= 7
    assert stats["compound_ids"] >= 3
    assert stats["queries_seeded"] >= 35

    paraphrase = CANONICAL_QUERIES["usd_eur"][1]
    section = Section(
        section_id="fx",
        category_slug="fx_rates",
        content=paraphrase,
        cache_policy=CachePolicy.REPLAY_SAFE,
    )
    decision = gate(
        paraphrase,
        section,
        runtime.cache,
        runtime.sidecar,
        coarse_threshold=0.88,
        verify_threshold=0.95,
    )
    assert decision.is_hit
    assert decision.value.get("rate") == 1.0


def test_warm_compound_paraphrase_hit():
    runtime = FinanceRuntime(tenant_id="test-warm-compound")
    warm_finance_corpus_cache(runtime, mode="all", use_live_rates=False)
    paraphrase = CANONICAL_QUERIES["compound_savings"][1]
    section = Section(
        section_id="compound",
        category_slug="compound_savings",
        content=paraphrase,
        cache_policy=CachePolicy.REPLAY_SAFE,
    )
    decision = gate(
        paraphrase,
        section,
        runtime.cache,
        runtime.sidecar,
        coarse_threshold=0.88,
        verify_threshold=0.95,
    )
    assert decision.is_hit
    assert "future_value" in decision.value


def test_hc2_cache_seed_phrases_wrapper():
    from benchmark.hc2.cache_helpers import cache_seed_phrases

    case = HealthcareCase(
        case_id="case-003-d4-01",
        presentation="BP 142/92, no meds.",
        expected_abstain=False,
        must_cite=["hypertension"],
        drugs=[],
        topic="hypertension",
        pipeline_depth=4,
        canonical_id="case-003",
    )
    phrases = cache_seed_phrases(case)
    assert len(phrases) >= 3
