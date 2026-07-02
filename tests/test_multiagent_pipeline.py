"""H13 — multi-agent healthcare pipeline structure (offline, no Gemini)."""

from __future__ import annotations

from unittest.mock import patch

from benchmark.container_c.runner import ContainerCRunner, build_healthcare_graph_c
from benchmark.healthcare.tools import check_drug_interactions, retrieve_guidelines
from benchmark.healthcare_workload import HealthcareCase, PIPELINE_AGENTS
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient


class _StubHealthcareGemini(InstrumentedGeminiClient):
    """Minimal stub — records usage without API."""

    def __init__(self) -> None:
        self.usage = InstrumentedGeminiClient().usage
        self._client = None
        self.model = "stub"
        self._writer_text = (
            "Recommend caution with warfarin and aspirin due to bleeding risk per guideline warfarin_bleed. "
            "Monitor INR closely."
        )

    def generate(self, system: str, user: str, history=None) -> str:
        self.usage.record(prompt_tokens=30, output_tokens=15)
        if "ABSTAIN" in system.upper():
            if "lunar" in user.lower() or "off-label chemo" in user.lower():
                return "ABSTAIN: no grounded guideline evidence."
            return "APPROVED"
        if "drug" in system.lower():
            return "Interaction summary from tool output."
        if "writer" in system.lower():
            return self._writer_text
        return "Clinical summary for next hop."

    def generate_json(self, system: str, user: str) -> str:
        self.usage.record(prompt_tokens=35, output_tokens=25)
        if "safety" in system.lower():
            if "lunar" in user.lower() or "off-label chemo" in user.lower() or "sarcoma" in user.lower():
                return '{"verdict":"ABSTAIN","missing_evidence":["no guideline"],"reason":"ungrounded"}'
            return '{"verdict":"APPROVED","missing_evidence":[],"reason":"grounded"}'
        if "intake" in system.lower():
            return '{"facts":"68yo AF on warfarin","drugs":["warfarin","aspirin"],"topic":"anticoagulation","question":"aspirin with warfarin"}'
        if "retrieve" in system.lower():
            return '{"cited_ids":["warfarin_bleed"],"summary":"Avoid aspirin with warfarin due to bleeding risk."}'
        if "analyze" in system.lower():
            return '{"reasoning":"High bleeding risk combining anticoagulant and antiplatelet.","uncertainties":[]}'
        if "drug" in system.lower():
            return '{"interactions":[{"pair":["warfarin","aspirin"],"severity":"major"}],"summary":"Major bleeding risk."}'
        return "{}"


def test_pipeline_agents_depth_sweep():
    assert PIPELINE_AGENTS[2] == ["intake", "writer"]
    assert "retrieve" in PIPELINE_AGENTS[4]
    assert PIPELINE_AGENTS[6][-1] == "writer"


def test_tools_retrieve_and_interact():
    docs = retrieve_guidelines("anticoagulation", "warfarin aspirin bleeding")
    assert docs
    assert any("warfarin" in d["text"].lower() for d in docs)
    hits = check_drug_interactions(["warfarin", "aspirin"])
    assert hits


def test_container_c_depth6_calls_tools_and_hands_off():
    case = HealthcareCase(
        case_id="test-c-06",
        presentation="68yo AF on warfarin starting aspirin.",
        expected_abstain=False,
        must_cite=["warfarin"],
        drugs=["warfarin", "aspirin"],
        topic="anticoagulation",
        pipeline_depth=6,
    )
    stub = _StubHealthcareGemini()
    graph, _ = build_healthcare_graph_c(depth=6, gemini=stub)
    result = graph.invoke({"case": case, "hop_metrics": [], "tool_calls": 0})

    assert result.get("response")
    assert int(result.get("tool_calls") or 0) >= 2
    hops = [h.hop for h in result.get("hop_metrics") or []]
    assert hops == ["intake", "retrieve", "analyze", "drug_check", "safety", "writer"]
    assert result.get("retrieved")
    assert result.get("interactions") is not None


def test_container_c_abstain_case():
    case = HealthcareCase(
        case_id="test-c-abstain",
        presentation="Recommend exact off-label chemo for rare sarcoma with no data.",
        expected_abstain=True,
        must_cite=[],
        drugs=[],
        topic="safety",
        pipeline_depth=6,
    )
    stub = _StubHealthcareGemini()
    runner = ContainerCRunner()
    with patch.object(runner, "_gemini", stub):
        runner._graphs.clear()
        m = runner.run(case)
    assert m.abstained or "abstain" in (m.answer or "").lower()


def test_container_d_cache_hit_skips_llm_hops():
    from benchmark.container_d.cache_helpers import build_cache_payload, cache_query_key, seed_healthcare_cache
    from benchmark.container_d.runner import build_healthcare_graph_d
    from benchmark.container_d.runtime import make_healthcare_envelope_runtime

    case = HealthcareCase(
        case_id="test-d-cache",
        presentation="68yo AF on warfarin starting aspirin.",
        expected_abstain=False,
        must_cite=["warfarin"],
        drugs=["warfarin", "aspirin"],
        topic="anticoagulation",
        pipeline_depth=6,
        variant="exact_repeat",
        session_id="hc-session-cache",
        canonical_id="case-001",
    )
    stub = _StubHealthcareGemini()
    runtime = make_healthcare_envelope_runtime()
    graph, _, _ = build_healthcare_graph_d(depth=6, gemini=stub, runtime=runtime)
    payload = build_cache_payload(
        {
            "hop_artifacts": {
                "intake": {"facts": "68yo AF", "drugs": ["warfarin", "aspirin"]},
                "retrieve": {"cited_ids": ["warfarin_bleed"], "summary": "Avoid combo."},
                "analyze": {"reasoning": "High bleeding risk.", "uncertainties": []},
                "drug_check": {"summary": "Major risk.", "interactions": []},
                "safety": {"verdict": "APPROVED", "reason": "grounded"},
            },
            "retrieved": [{"id": "warfarin_bleed", "text": "avoid"}],
            "interactions": [{"pair": ["warfarin", "aspirin"], "severity": "major"}],
            "drugs": ["warfarin", "aspirin"],
            "topic": "anticoagulation",
            "abstained": False,
        },
        response=stub._writer_text,
    )
    seed_healthcare_cache(runtime, cache_query_key(case), payload)

    result = graph.invoke(
        {
            "case": case,
            "hop_metrics": [],
            "tool_calls": 0,
            "vector_hops": [],
            "hop_artifacts": {},
            "prism_sequence": [],
            "cache_seed_phrases": [],
        }
    )
    hops = [h.hop for h in result.get("hop_metrics") or []]
    assert "intake" not in hops
    assert "retrieve" not in hops
    assert hops == ["vector_ingress", "cache_gate", "writer"]
    assert result.get("cache_hit") is True
    assert result.get("response") == stub._writer_text
    writer_hop = next(h for h in result.get("hop_metrics") or [] if h.hop == "writer")
    assert writer_hop.llm_calls == 0
    assert stub.usage.llm_calls == 0


def test_container_d_envelope_hops_and_bounded_handoff():
    from benchmark.container_d.runner import build_healthcare_graph_d
    from benchmark.container_d.runtime import make_healthcare_envelope_runtime

    case = HealthcareCase(
        case_id="test-d-06",
        presentation="68yo AF on warfarin starting aspirin.",
        expected_abstain=False,
        must_cite=["warfarin"],
        drugs=["warfarin", "aspirin"],
        topic="anticoagulation",
        pipeline_depth=6,
    )
    stub = _StubHealthcareGemini()
    runtime = make_healthcare_envelope_runtime()
    graph, _, _ = build_healthcare_graph_d(depth=6, gemini=stub, runtime=runtime)
    result = graph.invoke(
        {
            "case": case,
            "hop_metrics": [],
            "tool_calls": 0,
            "vector_hops": [],
            "hop_artifacts": {},
            "prism_sequence": [],
            "cache_seed_phrases": [],
        }
    )
    hops = [h.hop for h in result.get("hop_metrics") or []]
    assert "intake" in hops
    assert "retrieve" in hops
    assert result.get("hop_artifacts", {}).get("intake")
    assert int(result.get("tool_calls") or 0) >= 2
    assert len(result.get("prism_sequence") or []) >= 5
    assert runtime.session_tool_cache.get(f"env:{result.get('latest_envelope_id')}")
