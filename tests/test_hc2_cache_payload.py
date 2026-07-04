"""HC2 cache payload depth sufficiency + handoff fallbacks."""

from __future__ import annotations

from benchmark.hc2.artifacts import analyze_handoff_plain
from benchmark.hc2.cache_helpers import cache_payload_sufficient, cache_semantic_gate_query
from benchmark.healthcare_workload import HealthcareCase


def test_cache_semantic_gate_query_includes_depth():
    case = HealthcareCase(
        case_id="c1-d6-00",
        presentation="x",
        expected_abstain=False,
        must_cite=[],
        drugs=[],
        topic="diabetes",
        pipeline_depth=6,
        canonical_id="case-002",
    )
    q = cache_semantic_gate_query(case)
    assert "[pipeline_depth=6]" in q
    assert "diabetes:case-002" in q


def test_cache_payload_insufficient_for_depth6_intake_only():
    payload = {"hop_artifacts": {"intake": {"facts": "brief"}}, "retrieved": []}
    assert not cache_payload_sufficient(payload, 6)


def test_cache_payload_insufficient_for_depth4_intake_only():
    payload = {"hop_artifacts": {"intake": {"facts": "brief"}}, "retrieved": []}
    assert not cache_payload_sufficient(payload, 4)


def test_cache_payload_sufficient_for_depth6_with_retrieved():
    payload = {
        "hop_artifacts": {"intake": {"facts": "brief"}},
        "retrieved": [{"id": "doc-1", "text": "hold metformin"}],
    }
    assert cache_payload_sufficient(payload, 6)


def test_analyze_handoff_uses_state_retrieved_when_hop_missing():
    hop = {"intake": {"facts": "brief", "drugs": []}}
    docs = [{"id": "warfarin_bleed", "text": "avoid combo", "source": "kb"}]
    text = analyze_handoff_plain(hop, retrieved=docs)
    assert "warfarin_bleed" in text
    assert "retrieved_docs" in text
