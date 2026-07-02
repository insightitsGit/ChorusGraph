"""Tests for Container D artifact helpers."""

from __future__ import annotations

from benchmark.container_d.artifacts import (
    compact_artifact,
    envelope_handoff,
    safety_handoff_user,
    should_abstain,
    store_envelope_artifact,
    writer_handoff_user,
)
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime


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
    assert should_abstain(
        case_topic="safety",
        retrieve_artifact={"cited_ids": []},
        retrieved_docs=[],
        safety_verdict={"verdict": "APPROVED"},
    ) is True


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
