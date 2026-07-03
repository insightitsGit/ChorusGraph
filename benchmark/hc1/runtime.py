"""Lightweight runtime for HC1 — semantic cache only (no Cortex)."""

from __future__ import annotations

from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

HC1_TENANT_ID = "healthcare-benchmark-hc1"
GRAPH_ID = "healthcare-single-agent"


def make_healthcare_hc1_runtime(
    *,
    gemini=None,
    tenant_id: str = HC1_TENANT_ID,
) -> FinanceRuntime:
    return FinanceRuntime(tenant_id=tenant_id, gemini=gemini, enable_cortex=False)


__all__ = ["GRAPH_ID", "HC1_TENANT_ID", "make_healthcare_hc1_runtime"]
