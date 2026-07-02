"""Lightweight ChorusGraph runtime for healthcare envelope benchmarks (cache only)."""

from __future__ import annotations

from chorusgraph.examples.finance_agent.runtime import FinanceRuntime


def make_healthcare_envelope_runtime(
    tenant_id: str = "healthcare-benchmark-d",
) -> FinanceRuntime:
    """Cache + projector only — no Cortex cold-start (~450ms saved per graph build)."""
    return FinanceRuntime(tenant_id=tenant_id, enable_cortex=False)
