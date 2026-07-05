"""T5 — HC1 shared global cache offline proof (real graph, stub Gemini only)."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from benchmark.hc1.runner import HC1Runner, build_healthcare_graph_hc1
from benchmark.healthcare.fingerprint import clinical_fingerprint
from benchmark.healthcare_workload import generate_healthcare_workload
from benchmark.shared.healthcare_cache import gate_clinical, seed_clinical_cache_entry
from benchmark.shared.instrumented_gemini import LlmUsage
from chorusgraph.sections.profiles import default_registry


class _HC1OfflineGemini:
    """Stub InstrumentedGeminiClient — drives real HC1 react loop + writer offline."""

    _WRITER = (
        "Recommend warfarin and aspirin interaction counseling per warfarin_bleed "
        "guidelines with anticoagulation monitoring and bleeding risk discussion."
    )

    def __init__(self) -> None:
        self.usage = LlmUsage()
        self._react_step = 0

    def reset_usage(self) -> None:
        self.usage.reset()
        self._react_step = 0

    def generate_json(self, _system: str, _user: str) -> str:
        self.usage.record(prompt_tokens=40, output_tokens=30)
        if self._react_step == 0:
            self._react_step += 1
            return json.dumps(
                {
                    "thought": "retrieve guidelines",
                    "finish": False,
                    "action": {
                        "tool": "retrieve_guidelines",
                        "args": {"topic": "anticoagulation", "query": "warfarin aspirin"},
                    },
                }
            )
        self._react_step += 1
        return json.dumps({"thought": "done", "finish": True, "action": None})

    def generate(self, _system: str, _user: str, history=None) -> str:
        self.usage.record(prompt_tokens=35, output_tokens=20)
        return self._WRITER


def _make_runner(monkeypatch) -> HC1Runner:
    HC1Runner._shared_runtime = None
    monkeypatch.setattr("benchmark.hc1.runner.InstrumentedGeminiClient", _HC1OfflineGemini)
    runner = HC1Runner()
    compiled, _, _ = build_healthcare_graph_hc1(
        runtime=runner._runtime,
        gemini=runner._gemini,
        coarse_threshold=runner._thresholds.coarse,
        verify_threshold=runner._thresholds.verify_for("clinical_judgment"),
    )
    assert compiled is not None, "must exercise real build_healthcare_graph_hc1 graph"
    return runner


def test_hc1_two_pass_repeat_hit_rate_and_reduced_llm(monkeypatch):
    """
    Pass 1 warms global facts cache via real HC1 graph (novel cases).
    Pass 2 cross-session repeats must cache_hit=True with strictly fewer LLM calls.
    """
    cases = generate_healthcare_workload(18, seed=42, repeat_band_pct=40)
    runner = _make_runner(monkeypatch)

    cold_llm: dict[str, int] = {}
    seeded_canonicals: set[str] = set()
    for case in cases:
        m = runner.run(case)
        assert m.error is None, m.error
        if not m.cache_hit and case.canonical_id not in cold_llm:
            cold_llm[case.canonical_id] = m.llm_calls
            assert m.llm_calls >= 2, "cold path should exercise react + writer"
        if m.cache_hit:
            seeded_canonicals.add(case.canonical_id)
        elif not m.abstained:
            seeded_canonicals.add(case.canonical_id)

    repeat_source = [
        c
        for c in cases
        if c.variant in ("exact_repeat", "paraphrase") and c.canonical_id in seeded_canonicals
    ]
    assert repeat_source, "workload must include seedable repeat variants"

    pass2_cases = [
        replace(c, case_id=f"{c.case_id}-pass2", session_id=f"hc-pass2-{i:03d}")
        for i, c in enumerate(repeat_source)
    ]

    hit_rows = 0
    for case in pass2_cases:
        m = runner.run(case)
        assert m.error is None, m.error
        key = case.canonical_id
        assert key in cold_llm, f"missing cold baseline for canonical_id={key}"
        assert m.cache_hit is True, (
            f"expected cache hit for {case.variant} {case.case_id} "
            f"(canonical={case.canonical_id}, session={case.session_id})"
        )
        assert m.llm_calls < cold_llm[key], (
            f"expected reduced LLM calls on hit: got {m.llm_calls}, cold={cold_llm[key]}"
        )
        assert m.llm_calls == 1, "cache hit should skip react and run writer only"
        hit_rows += 1

    hit_rate = hit_rows / len(pass2_cases)
    assert hit_rate == 1.0, f"expected 100% hit rate on pass-2 repeats, got {hit_rate:.1%}"
    # Stored on module for handoff reporting
    pytest.hc1_offline_hit_rate = hit_rate  # type: ignore[attr-defined]


def test_judgment_fingerprint_miss_across_different_fingerprints():
    """Judgment entries keyed by fingerprint must not hit when fingerprint differs."""
    from benchmark.hc1.runtime import make_healthcare_hc1_runtime

    runtime = make_healthcare_hc1_runtime()
    session_id = "fp-negative-test"
    profile = default_registry().get("clinical_judgment")

    intake_a = {"drugs": ["warfarin"], "topic": "anticoagulation", "facts": "68yo AF on warfarin"}
    intake_b = {
        "drugs": ["warfarin", "aspirin"],
        "topic": "anticoagulation",
        "facts": "68yo AF on warfarin starting aspirin",
    }
    fp_a = clinical_fingerprint(intake_a, pipeline_depth=6, drugs=["warfarin"])
    fp_b = clinical_fingerprint(intake_b, pipeline_depth=6, drugs=["warfarin", "aspirin"])
    assert fp_a != fp_b

    seeded = seed_clinical_cache_entry(
        runtime,
        query=fp_a,
        payload={"retrieved": [{"id": "warfarin_bleed"}], "interactions": []},
        category_slug="clinical_judgment",
        profile=profile,
        session_id=session_id,
        fingerprint_key=fp_a,
        response="Approved warfarin counseling with bleeding risk per warfarin_bleed.",
        safety_verdict={"verdict": "APPROVED"},
    )
    assert seeded is True

    miss = gate_clinical(
        runtime,
        query=fp_b,
        category_slug="clinical_judgment",
        profile=profile,
        session_id=session_id,
        fingerprint_key=fp_b,
    )
    assert miss.is_hit is False

    hit = gate_clinical(
        runtime,
        query=fp_a,
        category_slug="clinical_judgment",
        profile=profile,
        session_id=session_id,
        fingerprint_key=fp_a,
    )
    assert hit.is_hit is True
