"""T6 — CacheProfile profiler tests (offline fixtures)."""

from __future__ import annotations

from benchmark.profiler import (
    FIXTURES_DIR,
    context_probe,
    load_fixture,
    profile_from_fixture,
    run_profiler,
    sensitivity_probe,
    volatility_probe,
)


def test_fx_rates_recommends_semantic_b_shape():
    data = load_fixture("fx_rates", fixtures_dir=FIXTURES_DIR)
    sens = sensitivity_probe(data)
    vol = volatility_probe(data)
    ctx = context_probe(data)
    assert sens["recommended_keying"] == "semantic"
    assert ctx["recommended_scope"] == "global"
    assert vol.get("recommended_ttl_s") is not None


def test_clinical_guidelines_recommends_fingerprint_c_shape():
    data = load_fixture("clinical_guidelines", fixtures_dir=FIXTURES_DIR)
    sens = sensitivity_probe(data)
    ctx = context_probe(data)
    profile, _ = profile_from_fixture("clinical_guidelines", fixtures_dir=FIXTURES_DIR)
    assert sens["recommended_keying"] == "fingerprint"
    assert ctx["context_sensitive"] is True
    assert profile.keying == "fingerprint"
    assert profile.risk_tier == "high"


def test_run_profiler_writes_manifest(tmp_path):
    manifest = run_profiler(
        ["fx_rates", "clinical_guidelines"],
        run_id="test_run",
        output_dir=tmp_path,
    )
    assert "fx_rates" in manifest["profiles"]
    assert (tmp_path / "profiler_manifest.json").exists()
    assert (tmp_path / "fx_rates_evidence.json").exists()
