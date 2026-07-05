"""Tests for finance and healthcare sample corpora."""

from __future__ import annotations

from benchmark.finance.corpus import (
    CANONICAL_QUERIES,
    COMPOUND_SCENARIOS,
    MEMORY_PROFILES,
)
from benchmark.finance.corpus import (
    corpus_stats as finance_stats,
)
from benchmark.healthcare.cases import CASES
from benchmark.healthcare.cases import corpus_stats as healthcare_stats
from benchmark.healthcare.kb import GUIDELINES
from benchmark.healthcare.tools import check_drug_interactions, retrieve_guidelines
from benchmark.healthcare_workload import generate_healthcare_workload
from benchmark.healthcare_workload import workload_stats as hc_workload_stats
from benchmark.rubric import score_by_canonical
from benchmark.workload import generate_workload, workload_stats


def test_finance_corpus_richness():
    stats = finance_stats()
    assert stats["total_canonical_ids"] >= 10
    assert stats["fx_canonical_ids"] >= 7
    assert stats["compound_canonical_ids"] >= 3
    assert stats["memory_profiles"] >= 5
    assert stats["total_phrases"] >= 40
    for cid, phrases in CANONICAL_QUERIES.items():
        assert len(phrases) >= 3, f"{cid} needs at least 3 phrasings"
        assert phrases[0].strip()


def test_finance_memory_profiles_complete():
    for profile_id, profile in MEMORY_PROFILES.items():
        assert profile.get("seed")
        recalls = profile.get("recalls") or []
        assert len(recalls) >= 2, profile_id
        assert profile.get("expected_terms")


def test_finance_compound_scenarios_match_queries():
    for cid in ("compound_savings", "compound_retirement", "compound_loan"):
        assert cid in CANONICAL_QUERIES
        assert cid in COMPOUND_SCENARIOS
        scenario = COMPOUND_SCENARIOS[cid]
        assert scenario["principal"] > 0
        assert scenario["years"] > 0


def test_healthcare_corpus_richness():
    stats = healthcare_stats()
    assert stats["total_cases"] >= 18
    assert stats["topics"] >= 10
    assert stats["abstain_cases"] >= 4
    assert stats["actionable_cases"] >= 12
    assert stats["missing_paraphrases"] == 0
    assert stats["total_paraphrase_phrases"] >= stats["total_cases"] * 2


def test_healthcare_kb_covers_case_topics():
    topics = {c["topic"] for c in CASES}
    kb_topics = {g["topic"] for g in GUIDELINES}
    # Safety topic uses abstain guidelines; every non-safety topic should have KB support.
    for topic in topics - {"safety"}:
        assert topic in kb_topics, f"missing guideline topic: {topic}"


def test_healthcare_drug_interactions_lookup():
    for case in CASES:
        drugs = case["drugs"]
        if len(drugs) < 2:
            continue
        hits = check_drug_interactions(drugs)
        # Known benchmark pairs must resolve when both drugs listed.
        if set(drugs) & {
            "warfarin",
            "aspirin",
            "lisinopril",
            "spironolactone",
            "simvastatin",
            "clarithromycin",
        }:
            assert hits or case["expected_abstain"]


def test_healthcare_retrieval_returns_docs():
    for case in CASES:
        if case["expected_abstain"]:
            docs = retrieve_guidelines("safety", case["presentation"])
            assert docs
            continue
        docs = retrieve_guidelines(case["topic"], case["presentation"])
        assert docs, case["case_id"]


def test_workload_generators_use_corpus():
    finance = generate_workload(24, seed=7, include_memory_tasks=True)
    fstats = workload_stats(finance)
    assert fstats["total"] == 24
    assert fstats["sessions"] >= 4

    healthcare = generate_healthcare_workload(24, seed=7)
    hstats = hc_workload_stats(healthcare)
    assert hstats["total"] == 24
    assert len({c.canonical_id for c in healthcare}) >= 6


def test_rubric_new_fx_and_compound_ids():
    assert score_by_canonical(
        canonical_id="usd_chf",
        message="USD/CHF rate?",
        answer="The USD to CHF exchange rate is 0.9012 today.",
    )
    assert score_by_canonical(
        canonical_id="compound_retirement",
        message="If I invest $50,000 at 6% annual interest compounded quarterly for 10 years, what is the future value?",
        answer="The future value is approximately $90,700.92 after 10 years.",
    )
