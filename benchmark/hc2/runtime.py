"""Lightweight ChorusGraph runtime for healthcare envelope benchmarks (cache only)."""

from __future__ import annotations

from benchmark.healthcare.retrieval import build_clinical_retrieval_backend
from chorusgraph.compose import ChorusStack
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime


def make_healthcare_envelope_runtime(
    tenant_id: str = "healthcare-benchmark-d",
) -> FinanceRuntime:
    """Cache + projector + clinical retrieval — no Cortex cold-start."""
    stack = ChorusStack.defaults(tenant_id=tenant_id, enable_memory=False).with_retrieval(
        build_clinical_retrieval_backend()
    )
    return FinanceRuntime(tenant_id=tenant_id, stack=stack, enable_cortex=False)
