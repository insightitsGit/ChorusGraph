"""Verify benchmark runners wire to latest H21 + HC2 routing implementation."""

from __future__ import annotations

import inspect
from typing import List


class BenchmarkWiringError(RuntimeError):
    """Benchmark harness is not connected to expected engine/benchmark code."""


def verify_benchmark_wiring() -> List[str]:
    """
    Preflight before ``run_scenarios`` — fail fast if runners miss H21 wiring.

    Returns human-readable confirmation lines (also printed by ``run_scenarios``).
    """
    ok: List[str] = []

    from benchmark.hc1.runner import HC1Runner, build_healthcare_graph_hc1
    from benchmark.hc2.cache_helpers import (
        apply_cache_payload,
        cached_response_from_state,
        first_judgment_hop_after_cache,
        gate_clinical,
        seed_healthcare_cache,
    )
    from benchmark.hc2.nodes import route_after_cache_hc2
    from benchmark.hc2.runner import HC2Runner, build_healthcare_graph_hc2
    from benchmark.shared.healthcare_cache import seed_clinical_cache_entry
    from chorusgraph.cache_gate.seed_policy import should_seed_cache
    from chorusgraph.sections.profiles import default_registry

    if not hasattr(HC1Runner, "_shared_runtime"):
        raise BenchmarkWiringError("HC1Runner missing _shared_runtime (H21 T5 global cache)")
    ok.append("HC1: shared global runtime (_shared_runtime)")

    if not hasattr(HC2Runner, "_shared_runtime"):
        raise BenchmarkWiringError("HC2Runner missing _shared_runtime")
    ok.append("HC2: shared runtime across sessions")

    sig = inspect.signature(route_after_cache_hc2)
    if "agents" not in sig.parameters:
        raise BenchmarkWiringError("route_after_cache_hc2 must accept agents= (depth-aware routing)")
    ok.append("HC2: depth-aware route_after_cache_hc2(agents=...)")

    if cached_response_from_state({"cache_hit": True, "cached_response": "x"}) is not None:
        raise BenchmarkWiringError("cached_response_from_state must not replay judgments (archetype C)")
    ok.append("HC2: no writer judgment replay from cache")

    merged = apply_cache_payload({"cache_hit": True}, {"retrieved": [{"id": "g1"}]})
    if not merged.get("cache_facts"):
        raise BenchmarkWiringError("apply_cache_payload must set cache_facts=True")
    ok.append("HC2: facts-only apply_cache_payload (cache_facts flag)")

    from benchmark.healthcare_workload import HealthcareCase, PIPELINE_AGENTS

    case6 = HealthcareCase(
        case_id="wiring-d6",
        presentation="test",
        expected_abstain=False,
        must_cite=[],
        drugs=[],
        topic="t",
        pipeline_depth=6,
    )
    hop6 = first_judgment_hop_after_cache(
        {"case": case6, "cache_hit": True, "cache_facts": True},
        PIPELINE_AGENTS[6],
    )
    if hop6 != "safety":
        raise BenchmarkWiringError(f"depth-6 cache hit must route to safety, got {hop6!r}")
    ok.append("HC2: depth-6 cache hit routes to safety (not writer-only)")

    reg = default_registry()
    for slug in ("fx_rates", "clinical_retrieval", "clinical_judgment"):
        if slug not in reg.slugs():
            raise BenchmarkWiringError(f"CacheProfile registry missing {slug}")
    ok.append("CacheProfile registry: fx_rates + clinical slugs")

    if gate_clinical is None or seed_clinical_cache_entry is None:
        raise BenchmarkWiringError("healthcare gate/seed helpers missing")
    ok.append("Healthcare: gate_clinical + seed_clinical_cache_entry")

    allowed, _ = should_seed_cache(response="Cannot provide a recommendation.", abstained=False)
    if allowed:
        raise BenchmarkWiringError("seed_policy must refuse writer refusal text")
    ok.append("Quality-gated seeding (refusal blocked)")

    # Compiled graph builders must be importable (benchmark uses these directly).
    assert callable(build_healthcare_graph_hc1)
    assert callable(build_healthcare_graph_hc2)
    ok.append("Graph builders: build_healthcare_graph_hc1/hc2")

    from chorusgraph.examples.finance_agent.nodes import make_cache_gate_handler

    assert callable(make_cache_gate_handler)
    ok.append("Finance: make_cache_gate_handler (CacheProfile-aware gate)")

    return ok


__all__ = ["BenchmarkWiringError", "verify_benchmark_wiring"]
