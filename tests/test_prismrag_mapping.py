"""T3 — PrismRAG mapping determinism (no license required for Mapping)."""

from __future__ import annotations

import pytest

from benchmark.healthcare.prismrag_mapping import (
    assign_clinical_category,
    build_clinical_mapping,
    build_clinical_mapping_dict,
)


def test_mapping_dict_has_categories_and_rules():
    d = build_clinical_mapping_dict()
    assert d["categories"]
    assert d["rules"]
    slugs = {c["slug"] for c in d["categories"]}
    assert "diabetes" in slugs
    assert "hypertension" in slugs


def test_assign_category_deterministic():
    a = assign_clinical_category("patient on warfarin with bleeding risk")
    b = assign_clinical_category("patient on warfarin with bleeding risk")
    assert a == b
    assert a == "anticoagulation"


def test_ambiguous_monitoring_resolves():
    cat = assign_clinical_category("routine monitoring of potassium")
    assert cat is not None


def test_mapping_build_idempotent():
    m1 = build_clinical_mapping()
    m2 = build_clinical_mapping()
    assert m1.assign_category("metformin diabetes") == m2.assign_category("metformin diabetes")


@pytest.mark.skipif(
    not __import__("os").environ.get("PRISMRAG_LICENSE_KEY"),
    reason="PRISMRAG_LICENSE_KEY not set",
)
def test_prismrag_patch_instantiation_when_licensed():
    from benchmark.healthcare.prismrag_mapping import try_create_prismrag_patch

    patch = try_create_prismrag_patch()
    assert patch is not None
    vec = [0.1] * 384
    out = patch.remap("warfarin bleeding", vec)
    assert len(out) == 384
