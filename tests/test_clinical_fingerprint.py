"""T3 — Clinical fingerprint keying tests."""

from __future__ import annotations

from benchmark.healthcare.fingerprint import clinical_fingerprint


def test_paraphrase_same_fingerprint():
    intake_a = {"drugs": ["warfarin", "aspirin"], "topic": "anticoagulation", "facts": "68yo AF on warfarin"}
    intake_b = {
        "drugs": ["aspirin", "warfarin"],
        "topic": "anticoagulation",
        "facts": "elderly patient anticoagulated with warfarin asking about aspirin",
    }
    fp_a = clinical_fingerprint(intake_a, pipeline_depth=4)
    fp_b = clinical_fingerprint(intake_b, pipeline_depth=4)
    assert fp_a == fp_b


def test_different_drug_different_fingerprint():
    base = {"drugs": ["metformin"], "topic": "diabetes", "facts": "eGFR 55"}
    changed = {"drugs": ["metformin", "contrast_iv"], "topic": "diabetes", "facts": "eGFR 55"}
    assert clinical_fingerprint(base, pipeline_depth=6) != clinical_fingerprint(changed, pipeline_depth=6)


def test_k_lab_bin_changes_fingerprint():
    base = {"drugs": [], "topic": "electrolyte", "facts": "K+ 4.3 stable"}
    delta = {"drugs": [], "topic": "electrolyte", "facts": "K+ 5.8 elevated"}
    assert clinical_fingerprint(base, pipeline_depth=4) != clinical_fingerprint(delta, pipeline_depth=4)
