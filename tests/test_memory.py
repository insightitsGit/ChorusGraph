"""Cortex long-term memory tests."""

from __future__ import annotations

import time

import pytest

from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key
from chorusgraph.examples.finance_agent.graph import build_finance_graph, turn_input
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime
from chorusgraph.memory import get_cortex_service
from chorusgraph import SqliteLedgerSink, wrap
from chorusgraph.examples.finance_agent.graph import GRAPH_ID, TENANT_ID
from prismcortex.models import DigestOutcome


def test_cortex_skips_trivial_salience(tmp_path):
    svc = get_cortex_service(tenant_id="salience-test", cache_dir=str(tmp_path / "cortex-a"))
    result = svc.ensure_memory().digest("ok thanks", source_id="trivial-1", agent_id="test")
    assert result.outcome == DigestOutcome.SKIPPED
    assert "low salience" in (result.reason or "")


def test_async_digest_returns_immediately(tmp_path):
    svc = get_cortex_service(tenant_id="async-test", cache_dir=str(tmp_path / "cortex-b"))
    started = time.perf_counter()
    svc.schedule_digest("Thanks!", source_id="async-1")
    elapsed = time.perf_counter() - started
    assert elapsed < 0.25
    svc.wait_for_digest(timeout=30)


@pytest.mark.skipif(not resolve_gemini_api_key(), reason="GEMINI_API_KEY not configured")
def test_cross_session_recall_with_provenance(tmp_path):
    cortex_dir = tmp_path / "cortex-cross"
    cortex = get_cortex_service(tenant_id="cross-session", cache_dir=str(cortex_dir))

    runtime = FinanceRuntime(tenant_id="cross-session", cortex_cache_dir=str(cortex_dir))
    compiled, _ = build_finance_graph(runtime)
    wrapped = wrap(compiled, tenant_id=TENANT_ID, graph_id=GRAPH_ID, sink=SqliteLedgerSink(":memory:"))

    config1 = {"configurable": {"thread_id": "session-one"}}
    config2 = {"configurable": {"thread_id": "session-two"}}

    s1 = wrapped.invoke(
        turn_input(
            "My risk tolerance is conservative. I prefer low-volatility investments.",
            turn_id="s1-t1",
        ),
        config=config1,
    )
    runtime.schedule_turn_digest(
        "My risk tolerance is conservative. I prefer low-volatility investments.",
        s1.get("response", ""),
        turn_id="s1-t1",
    )
    cortex.wait_for_digest(timeout=120)

    explain = cortex.explain("What is my risk tolerance?")
    assert explain.evidence
    assert explain.confidence > 0

    s2 = wrapped.invoke(
        turn_input("What bond allocation would you recommend for me?", turn_id="s2-t1"),
        config=config2,
    )
    assert s2.get("memory_recall")
    assert s2.get("memory_confidence") is not None

    writer_step = next((st for st in wrapped.last_ledger.steps if st.node == "writer"), None)
    assert writer_step is not None
    assert writer_step.grounding_score == s2.get("memory_confidence")

    answer = (s2.get("response") or "").lower()
    recall = (s2.get("memory_recall") or "").lower()
    assert "conservative" in recall or "conservative" in answer
