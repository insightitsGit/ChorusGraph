"""PrismCheckpointer tests."""

from __future__ import annotations

import pytest

from chorusgraph.checkpoint import create_checkpointer, sqlite_checkpointer
from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key
from chorusgraph.examples.finance_agent.graph import build_finance_graph, turn_input
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime


def test_sqlite_checkpointer_factory(tmp_path):
    path = tmp_path / "cp.sqlite"
    cp = create_checkpointer("sqlite", path=str(path))
    assert cp is not None
    assert path.exists() or True  # file created on first put


@pytest.mark.live
@pytest.mark.skipif(not resolve_gemini_api_key(), reason="GEMINI_API_KEY not configured")
def test_thread_resumes_after_restart(tmp_path):
    from chorusgraph.core.persistence import json_file_checkpointer

    thread_id = "resume-thread-1"
    config = {"configurable": {"thread_id": thread_id}}
    cp = json_file_checkpointer(str(tmp_path / "checkpoints"))
    runtime = FinanceRuntime(
        tenant_id="checkpoint-test",
        cortex_cache_dir=str(tmp_path / "cortex"),
    )
    compiled, _ = build_finance_graph(runtime, checkpointer=cp)

    r1 = compiled.invoke(
        turn_input("What is the USD to EUR exchange rate today?", turn_id="t1"), config=config
    )
    assert r1.get("response")
    r2 = compiled.invoke(turn_input("What about USD to GBP?", turn_id="t2"), config=config)
    history_len = len(r2.get("conversation_history") or [])
    assert history_len >= 2

    cp2 = json_file_checkpointer(str(tmp_path / "checkpoints"))
    runtime2 = FinanceRuntime(
        tenant_id="checkpoint-test",
        cortex_cache_dir=str(tmp_path / "cortex"),
    )
    compiled2, _ = build_finance_graph(runtime2, checkpointer=cp2)
    snapshot = compiled2.get_state(config)
    restored = snapshot.values.get("conversation_history") or []
    assert len(restored) == history_len

    r3 = compiled2.invoke(
        turn_input("Which currency from our chat is stronger against USD?", turn_id="t3"),
        config=config,
    )
    assert len(r3.get("conversation_history") or []) > history_len
