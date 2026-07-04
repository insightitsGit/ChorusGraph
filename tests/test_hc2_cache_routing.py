"""HC2 depth-aware cache routing tests."""

from __future__ import annotations

from benchmark.hc2.cache_helpers import first_judgment_hop_after_cache
from benchmark.healthcare_workload import HealthcareCase, PIPELINE_AGENTS


def test_first_judgment_hop_depth6_runs_analyze_when_missing():
    case = HealthcareCase(
        case_id="r1",
        presentation="test",
        expected_abstain=False,
        must_cite=[],
        drugs=[],
        topic="t",
        pipeline_depth=6,
    )
    agents = PIPELINE_AGENTS[6]
    hop = first_judgment_hop_after_cache({"case": case, "cache_hit": True, "cache_facts": True}, agents)
    assert hop == "analyze"


def test_first_judgment_hop_depth6_runs_safety_when_analyze_present():
    case = HealthcareCase(
        case_id="r1b",
        presentation="test",
        expected_abstain=False,
        must_cite=[],
        drugs=[],
        topic="t",
        pipeline_depth=6,
    )
    agents = PIPELINE_AGENTS[6]
    hop = first_judgment_hop_after_cache(
        {
            "case": case,
            "cache_hit": True,
            "cache_facts": True,
            "hop_artifacts": {"analyze": {"reasoning": "grounded"}},
        },
        agents,
    )
    assert hop == "safety"


def test_first_judgment_hop_depth6_empty_analyze_dict_reruns_analyze():
    """Empty {} from failed JSON parse must not skip analyze."""
    case = HealthcareCase(
        case_id="r1c",
        presentation="test",
        expected_abstain=False,
        must_cite=[],
        drugs=[],
        topic="t",
        pipeline_depth=6,
    )
    hop = first_judgment_hop_after_cache(
        {
            "case": case,
            "cache_hit": True,
            "cache_facts": True,
            "hop_artifacts": {"analyze": {}},
        },
        PIPELINE_AGENTS[6],
    )
    assert hop == "analyze"


def test_first_judgment_hop_depth4_runs_analyze():
    case = HealthcareCase(
        case_id="r2",
        presentation="test",
        expected_abstain=False,
        must_cite=[],
        drugs=[],
        topic="t",
        pipeline_depth=4,
    )
    agents = PIPELINE_AGENTS[4]
    hop = first_judgment_hop_after_cache({"case": case, "cache_hit": True, "cache_facts": True}, agents)
    assert hop == "analyze"


def test_first_judgment_hop_depth2_runs_writer():
    case = HealthcareCase(
        case_id="r3",
        presentation="test",
        expected_abstain=False,
        must_cite=[],
        drugs=[],
        topic="t",
        pipeline_depth=2,
    )
    agents = PIPELINE_AGENTS[2]
    hop = first_judgment_hop_after_cache({"case": case, "cache_hit": True, "cache_facts": True}, agents)
    assert hop == "writer"
