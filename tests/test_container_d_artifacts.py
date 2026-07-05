"""Tests for HC2 artifact helpers."""

from __future__ import annotations

from benchmark.hc2.artifacts import (
    analyze_handoff_plain,
    compact_artifact,
    envelope_handoff,
    retrieve_handoff_plain,
    safety_handoff_user,
    should_abstain,
    store_envelope_artifact,
    writer_handoff_user,
)
from benchmark.hc2.cache_helpers import cached_response_from_state
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime


def test_cached_response_from_state():
    """H21 archetype C — judgment responses are never replayed from cache."""
    state = {
        "cache_hit": True,
        "cached_response": "Cached clinical answer.",
    }
    assert cached_response_from_state(state) is None
    state2 = {"cache_hit": True, "response": "From response field."}
    assert cached_response_from_state(state2) is None
    assert cached_response_from_state({"cache_hit": False, "response": "x"}) is None


def test_plain_handoffs_are_compact():
    hop = {
        "intake": {"facts": "brief", "drugs": ["warfarin"]},
        "retrieve": {"cited_ids": ["warfarin_bleed"], "summary": "avoid combo"},
    }
    retrieve_text = retrieve_handoff_plain(hop, [{"id": "warfarin_bleed", "text": "avoid"}])
    analyze_text = analyze_handoff_plain(hop)
    assert len(retrieve_text) < 300
    assert len(analyze_text) < 300
    assert "previous_envelope_id" not in retrieve_text


def test_envelope_handoff_has_no_upstream_blob():
    text = envelope_handoff(
        hop="analyze",
        envelope_id="env-1",
        hop_input={"intake": {"facts": "brief"}},
    )
    assert "upstream" not in text
    assert "previous_envelope_id" in text
    assert len(text) < 200


def test_compact_artifact_by_source_hop():
    retrieve = {"cited_ids": ["a"], "summary": "short"}
    assert compact_artifact("retrieve", retrieve)["cited_ids"] == ["a"]
    intake = {"facts": "x" * 500, "drugs": []}
    assert len(compact_artifact("intake", intake)["facts"]) <= 200


def test_safety_handoff_is_compact():
    big_tree = {
        "intake": {"facts": "x" * 500, "drugs": ["warfarin"], "question": "q"},
        "retrieve": {"cited_ids": ["warfarin_bleed"], "summary": "y" * 500},
        "analyze": {"reasoning": "z" * 500, "uncertainties": []},
        "drug_check": {
            "summary": "major",
            "interactions": [{"pair": ["warfarin", "aspirin"], "severity": "major"}],
        },
    }
    text = safety_handoff_user(
        envelope_id="env-9",
        hop_artifacts=big_tree,
    )
    assert "upstream" not in text
    assert len(text) < 950


def test_writer_handoff_is_compact():
    text = writer_handoff_user(
        envelope_id="env-9",
        hop_artifacts={
            "intake": {"facts": "brief", "drugs": ["warfarin"]},
            "retrieve": {"cited_ids": ["warfarin_bleed"], "summary": "avoid combo"},
            "drug_check": {"summary": "major bleeding risk", "interactions": []},
            "safety": {"verdict": "APPROVED", "reason": "grounded"},
        },
    )
    assert "upstream" not in text
    assert len(text) < 500


def test_store_and_resolve_envelope_artifact():
    runtime = FinanceRuntime(tenant_id="env-store-test", enable_cortex=False)
    store_envelope_artifact(runtime, "env-42", {"facts": "stored"})
    assert runtime.session_tool_cache["env:env-42"]["facts"] == "stored"


def test_should_abstain_safety_topic_without_citations():
    assert (
        should_abstain(
            case_topic="safety",
            retrieve_artifact={"cited_ids": []},
            retrieved_docs=[],
            safety_verdict={"verdict": "APPROVED"},
        )
        is True
    )


def test_should_abstain_honors_approved_verdict():
    assert not should_abstain(
        case_topic="anticoagulation",
        retrieve_artifact={"cited_ids": ["warfarin_bleed"]},
        retrieved_docs=[{"id": "warfarin_bleed"}],
        safety_verdict={"verdict": "APPROVED", "missing_evidence": ["minor gap"]},
    )

    assert should_abstain(
        case_topic="hypertension",
        retrieve_artifact={"cited_ids": ["htn_stage2"]},
        retrieved_docs=[{"id": "htn_stage2"}],
        safety_verdict={"verdict": "ABSTAIN", "missing_evidence": ["x"]},
    )
