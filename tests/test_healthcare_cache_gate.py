"""T1 — Healthcare cache gate fingerprint + semantic dual lookup."""

from __future__ import annotations

from benchmark.healthcare.cache_gate import gate_healthcare_case
from benchmark.healthcare_workload import HealthcareCase
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime


def test_gate_healthcare_case_miss_without_seed():
    runtime = FinanceRuntime(tenant_id="gate-test")
    case = HealthcareCase(
        case_id="g1",
        presentation="warfarin aspirin interaction",
        expected_abstain=False,
        must_cite=[],
        drugs=["warfarin", "aspirin"],
        topic="anticoagulation",
        pipeline_depth=4,
    )
    decision = gate_healthcare_case(runtime, case, coarse_threshold=0.88, verify_threshold=0.95)
    assert not decision.is_hit
