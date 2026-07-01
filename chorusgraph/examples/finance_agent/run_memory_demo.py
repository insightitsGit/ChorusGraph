"""Memory demo — thread resume (checkpointer) + cross-session Cortex recall."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from chorusgraph import SqliteLedgerSink, wrap
from chorusgraph.checkpoint import create_checkpointer
from chorusgraph.examples.finance_agent.graph import (
    GRAPH_ID,
    TENANT_ID,
    build_finance_graph,
    turn_input,
)
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime
from chorusgraph.memory import get_cortex_service


def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def _print_turn(label: str, result: Dict[str, Any], ledger_path: List[str]) -> None:
    print(f"\n--- {label} ---")
    print("Question:", result.get("message") or "(checkpointed thread)")
    print("Answer:", result.get("response", ""))
    print("Memory recall:", result.get("memory_recall"))
    print("Memory confidence:", result.get("memory_confidence"))
    print("History turns:", len(result.get("conversation_history") or []))
    print("Ledger path:", " -> ".join(ledger_path))
    if ledger_path:
        print("Rule chain:", result.get("rule_chain"))


def _invoke_turn(
    wrapped,
    runtime: FinanceRuntime,
    message: str,
    config: Dict[str, Any],
    *,
    turn_id: str,
) -> Dict[str, Any]:
    result = wrapped.invoke(turn_input(message, turn_id=turn_id), config=config)
    runtime.schedule_turn_digest(message, result.get("response", ""), turn_id=turn_id)
    path = [s.node for s in wrapped.last_ledger.steps] if wrapped.last_ledger else []
    writer_step = next((s for s in wrapped.last_ledger.steps if s.node == "writer"), None)
    if writer_step and writer_step.grounding_score is not None:
        print(f"Ledger writer grounding_score: {writer_step.grounding_score}")
    return {**result, "message": message, "_path": path}


def demo_thread_resume(checkpoint_path: Path) -> Dict[str, Any]:
    _print_section("Demo A — Thread resume after process restart (PrismCheckpointer / SQLite)")
    thread_id = f"finance-thread-{uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    conn = sqlite3.connect(str(checkpoint_path), check_same_thread=False)
    cp = create_checkpointer("sqlite", conn=conn)
    runtime = FinanceRuntime(tenant_id="finance-resume-demo", cortex_cache_dir=str(checkpoint_path.parent / "cortex-resume"))
    compiled, _ = build_finance_graph(runtime, checkpointer=cp)
    wrapped = wrap(compiled, tenant_id=TENANT_ID, graph_id=GRAPH_ID, sink=SqliteLedgerSink(":memory:"))

    t1 = _invoke_turn(
        wrapped,
        runtime,
        "What is the USD to EUR exchange rate today?",
        config,
        turn_id="turn-1",
    )
    t2 = _invoke_turn(
        wrapped,
        runtime,
        "What about USD to GBP?",
        config,
        turn_id="turn-2",
    )
    history_len_before = len(t2.get("conversation_history") or [])
    conn.close()

    print("\n>>> Simulating process restart (new connection, same SQLite checkpoint file) <<<")
    conn2 = sqlite3.connect(str(checkpoint_path), check_same_thread=False)
    cp2 = create_checkpointer("sqlite", conn=conn2)
    runtime2 = FinanceRuntime(tenant_id="finance-resume-demo", cortex_cache_dir=str(checkpoint_path.parent / "cortex-resume"))
    compiled2, _ = build_finance_graph(runtime2, checkpointer=cp2)
    wrapped2 = wrap(compiled2, tenant_id=TENANT_ID, graph_id=GRAPH_ID, sink=SqliteLedgerSink(":memory:"))

    snapshot = compiled2.get_state(config)
    restored_history = snapshot.values.get("conversation_history") or []
    print(f"Restored conversation_history entries: {len(restored_history)}")

    t3 = _invoke_turn(
        wrapped2,
        runtime2,
        "Given our earlier rates, which is stronger against USD — EUR or GBP?",
        config,
        turn_id="turn-3",
    )
    conn2.close()

    return {
        "thread_id": thread_id,
        "history_before_restart": history_len_before,
        "history_after_restart": len(restored_history),
        "turn3_history": len(t3.get("conversation_history") or []),
        "turn1": t1,
        "turn2": t2,
        "turn3": t3,
    }


def demo_cross_session_recall(cortex_dir: Path) -> Dict[str, Any]:
    _print_section("Demo B — Cross-session Cortex recall (new thread, same memory service)")
    cortex = get_cortex_service(tenant_id="finance-cortex-demo", cache_dir=str(cortex_dir))

    session1_thread = f"session-1-{uuid4().hex[:8]}"
    session2_thread = f"session-2-{uuid4().hex[:8]}"
    config1 = {"configurable": {"thread_id": session1_thread}}
    config2 = {"configurable": {"thread_id": session2_thread}}

    runtime = FinanceRuntime(tenant_id="finance-cortex-demo", cortex_cache_dir=str(cortex_dir))
    compiled, _ = build_finance_graph(runtime)
    wrapped = wrap(compiled, tenant_id=TENANT_ID, graph_id=GRAPH_ID, sink=SqliteLedgerSink(":memory:"))

    pref_msg = "My risk tolerance is conservative. I prefer low-volatility investments and capital preservation."
    s1 = _invoke_turn(wrapped, runtime, pref_msg, config1, turn_id="session1-turn1")
    print("\nWaiting for async Cortex digest (off response path)...")
    cortex.wait_for_digest(timeout=120)

    explain = cortex.explain("What is my risk tolerance?")
    evidence = [{"fact": e.fact, "confidence": e.confidence, "source_id": e.source_id} for e in explain.evidence]

    bond_msg = "What kind of bond allocation would you recommend for me?"
    s2 = _invoke_turn(wrapped, runtime, bond_msg, config2, turn_id="session2-turn1")

    return {
        "session1_thread": session1_thread,
        "session2_thread": session2_thread,
        "session1_answer": s1.get("response"),
        "session2_answer": s2.get("response"),
        "session2_memory_recall": s2.get("memory_recall"),
        "session2_memory_confidence": s2.get("memory_confidence"),
        "explain_confidence": explain.confidence,
        "explain_evidence": evidence,
        "session2": s2,
    }


def run_memory_demo() -> Dict[str, Any]:
    base = Path(tempfile.mkdtemp(prefix="chorusgraph-memory-"))
    checkpoint_path = base / "checkpoints.sqlite"
    cortex_dir = base / "cortex"

    resume = demo_thread_resume(checkpoint_path)
    recall = demo_cross_session_recall(cortex_dir)

    _print_section("Summary")
    print("Thread resume:")
    print(json.dumps(
        {
            "thread_id": resume["thread_id"],
            "history_before_restart": resume["history_before_restart"],
            "history_after_restart": resume["history_after_restart"],
            "turn3_history": resume["turn3_history"],
            "turn3_answer": resume["turn3"].get("response"),
        },
        indent=2,
    ))
    print("\nCross-session recall:")
    print(json.dumps(
        {
            "session2_memory_recall": recall["session2_memory_recall"],
            "session2_memory_confidence": recall["session2_memory_confidence"],
            "explain_confidence": recall["explain_confidence"],
            "explain_evidence": recall["explain_evidence"],
            "session2_answer": recall["session2_answer"],
        },
        indent=2,
    ))
    return {"resume": resume, "recall": recall, "workdir": str(base)}


def main() -> None:
    try:
        run_memory_demo()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
