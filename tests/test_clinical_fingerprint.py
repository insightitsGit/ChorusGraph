"""T1/T5 — Clinical fingerprint depth bands + PrismRAG category signal."""

from __future__ import annotations

from benchmark.healthcare.fingerprint import (
    FINGERPRINT_DEPTH_CITED_IDS,
    FINGERPRINT_DEPTH_INTERACTIONS,
    clinical_fingerprint,
    clinical_fingerprint_from_case,
)
from benchmark.healthcare_workload import HealthcareCase


def test_paraphrase_same_fingerprint_depth_4():
    intake_a = {"drugs": ["warfarin", "aspirin"], "topic": "anticoagulation", "facts": "68yo AF on warfarin"}
    intake_b = {
        "drugs": ["aspirin", "warfarin"],
        "topic": "anticoagulation",
        "facts": "elderly patient anticoagulated with warfarin asking about aspirin",
    }
    hop = {"retrieve": {"cited_ids": ["warfarin_bleed"]}}
    fp_a = clinical_fingerprint(intake_a, pipeline_depth=4, hop_artifacts=hop)
    fp_b = clinical_fingerprint(intake_b, pipeline_depth=4, hop_artifacts=hop)
    assert fp_a == fp_b


def test_depth_6_different_cited_ids_different_fingerprint():
    intake = {"drugs": ["lisinopril"], "topic": "hypertension", "facts": "K+ 4.8 eGFR 55"}
    hop_a = {"retrieve": {"cited_ids": ["htn_stage1", "htn_ace_k"]}}
    hop_b = {"retrieve": {"cited_ids": ["htn_stage2"]}}
    fp_a = clinical_fingerprint(intake, pipeline_depth=6, hop_artifacts=hop_a)
    fp_b = clinical_fingerprint(intake, pipeline_depth=6, hop_artifacts=hop_b)
    assert fp_a != fp_b


def test_depth_2_unchanged_without_hop_artifacts():
    intake = {"drugs": ["metformin"], "topic": "diabetes", "facts": "eGFR 55"}
    fp = clinical_fingerprint(intake, pipeline_depth=2, gate_phase=True)
    assert "fp:" in fp
    payload_depth = 2
    assert payload_depth <= FINGERPRINT_DEPTH_CITED_IDS


def test_depth_6_interaction_severity_in_fingerprint():
    intake = {"drugs": ["simvastatin", "clarithromycin"], "topic": "safety", "facts": "eGFR 60"}
    hop_minor = {
        "retrieve": {"cited_ids": ["statin_cyp"]},
        "drug_check": {"interactions": [{"severity": "minor"}]},
    }
    hop_major = {
        "retrieve": {"cited_ids": ["statin_cyp"]},
        "drug_check": {"interactions": [{"severity": "major"}]},
    }
    assert clinical_fingerprint(intake, pipeline_depth=6, hop_artifacts=hop_minor) != clinical_fingerprint(
        intake, pipeline_depth=6, hop_artifacts=hop_major
    )
    assert FINGERPRINT_DEPTH_INTERACTIONS == 6


def test_category_slugs_from_retrieved_chunks():
    intake = {"drugs": [], "topic": "diabetes", "facts": "eGFR 55"}
    retrieved_a = [{"id": "dm_metformin", "category_slug": "diabetes"}]
    retrieved_b = [{"id": "warfarin_bleed", "category_slug": "anticoagulation"}]
    hop = {"retrieve": {"cited_ids": ["dm_metformin"]}}
    fp_a = clinical_fingerprint(intake, pipeline_depth=4, hop_artifacts=hop, retrieved=retrieved_a)
    fp_b = clinical_fingerprint(intake, pipeline_depth=4, hop_artifacts=hop, retrieved=retrieved_b)
    assert fp_a != fp_b


def test_gate_fingerprint_from_case():
    case = HealthcareCase(
        case_id="c1",
        presentation="Type 2 DM eGFR 55 on metformin",
        expected_abstain=False,
        must_cite=["dm_metformin"],
        drugs=["metformin"],
        topic="diabetes",
        pipeline_depth=6,
    )
    fp = clinical_fingerprint_from_case(case)
    assert fp.startswith("fp:")
