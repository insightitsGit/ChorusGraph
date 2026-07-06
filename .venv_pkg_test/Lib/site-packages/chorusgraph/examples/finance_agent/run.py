"""Run finance agent demo — 2-turn conversation with Route Ledger."""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

from chorusgraph import SqliteLedgerSink, wrap
from chorusgraph.examples.finance_agent.graph import GRAPH_ID, TENANT_ID, build_finance_graph, initial_state


def _print_turn(label: str, result: Dict[str, Any], ledger_path: List[str]) -> None:
    print(f"\n=== {label} ===")
    print("Question:", result.get("message") or "(from history)")
    print("Answer:", result.get("response", ""))
    print("Tool calls:", json.dumps(result.get("tool_calls") or [], indent=2))
    print("Cache hit:", result.get("cache_hit"))
    print("Validation:", json.dumps(result.get("validation") or {}, indent=2))
    print("Ledger path:", " -> ".join(ledger_path))
    print("Rule chain:", result.get("rule_chain"))


def run_two_turn_demo() -> Dict[str, Any]:
    compiled, runtime = build_finance_graph()
    sink = SqliteLedgerSink(":memory:")
    wrapped = wrap(compiled, tenant_id=TENANT_ID, graph_id=GRAPH_ID, sink=sink)

    # Turn 1
    t1_msg = "What is the USD to EUR exchange rate today?"
    r1 = wrapped.invoke(initial_state(t1_msg))
    path1 = [s.node for s in wrapped.last_ledger.steps] if wrapped.last_ledger else []
    _print_turn("Turn 1", {**r1, "message": t1_msg}, path1)

    history: List[Dict[str, str]] = [
        {"role": "user", "content": t1_msg},
        {"role": "assistant", "content": r1.get("response", "")},
    ]

    # Turn 2 — references turn 1 via conversation_history
    t2_msg = "What about USD to GBP?"
    r2 = wrapped.invoke(initial_state(t2_msg, conversation_history=history))
    path2 = [s.node for s in wrapped.last_ledger.steps] if wrapped.last_ledger else []
    _print_turn("Turn 2", {**r2, "message": t2_msg}, path2)

    # Turn 3 — repeat turn-1 query to exercise functional cache hit (same runtime)
    t3_msg = "What is the USD to EUR exchange rate today?"
    r3 = wrapped.invoke(initial_state(t3_msg, conversation_history=history))
    path3 = [s.node for s in wrapped.last_ledger.steps] if wrapped.last_ledger else []
    _print_turn("Turn 3 (cache probe)", {**r3, "message": t3_msg}, path3)

    return {"turn1": r1, "turn2": r2, "turn3": r3, "path1": path1, "path2": path2, "path3": path3}


def main() -> None:
    try:
        run_two_turn_demo()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
