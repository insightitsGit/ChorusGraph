"""Demo all three execution patterns with observable ledger traces."""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

from chorusgraph import SqliteLedgerSink, wrap
from chorusgraph.examples.finance_agent.patterns_graph import (
    GRAPH_ID,
    TENANT_ID,
    build_plan_solve_graph,
    build_react_graph,
    build_reflection_graph,
    pattern_initial_state,
)


def _print_trace(label: str, result: Dict[str, Any], ledger_nodes: List[str]) -> None:
    print(f"\n=== {label} ===")
    print("Question:", result.get("message"))
    print("Answer:", result.get("response", ""))
    print("Tool calls:", len(result.get("tool_calls") or []))
    for tc in result.get("tool_calls") or []:
        print(f"  - {tc.get('tool')} ok={tc.get('ok')} data={tc.get('data')}")
    print("Agent trace steps:", len(result.get("agent_trace") or []))
    print("Ledger path:", " -> ".join(ledger_nodes))
    trace_kinds = [n.split("/", 1)[-1] for n in ledger_nodes if "/" in n]
    print("Trace kinds in ledger:", trace_kinds)


def _run_pattern(name: str, compiled, runtime, message: str, **extra) -> Dict[str, Any]:
    wrapped = wrap(compiled, tenant_id=TENANT_ID, graph_id=f"{GRAPH_ID}-{name}", sink=SqliteLedgerSink(":memory:"))
    result = wrapped.invoke(pattern_initial_state(message, **extra))
    nodes = [s.node for s in wrapped.last_ledger.steps] if wrapped.last_ledger else []
    _print_trace(name.upper(), {**result, "message": message}, nodes)
    return {"result": result, "ledger_nodes": nodes, "ledger": wrapped.last_ledger}


def run_patterns_demo() -> Dict[str, Any]:
    outputs: Dict[str, Any] = {}

    compiled, runtime = build_react_graph()
    outputs["react"] = _run_pattern(
        "react",
        compiled,
        runtime,
        "Compare USD to EUR and USD to GBP exchange rates and tell me which currency is stronger against USD.",
    )
    assert len(outputs["react"]["result"].get("tool_calls") or []) >= 2

    compiled, runtime = build_reflection_graph()
    outputs["reflection"] = _run_pattern(
        "reflection",
        compiled,
        runtime,
        "What are the USD to EUR and USD to GBP rates today? Summarize which is stronger against USD.",
        reflection_demo_wrong_figure=True,
        reflection_pass=0,
    )
    val = outputs["reflection"]["result"].get("validation") or {}
    assert val.get("passes", 0) >= 1

    compiled, runtime = build_plan_solve_graph()
    outputs["plan_solve"] = _run_pattern(
        "plan_solve",
        compiled,
        runtime,
        "Fetch USD to EUR and USD to GBP rates, compute the EUR/GBP cross-rate, and summarize.",
    )
    assert outputs["plan_solve"]["result"].get("plan_steps")

    print("\n=== Summary (reasoning traces) ===")
    for key in ("react", "reflection", "plan_solve"):
        nodes = outputs[key]["ledger_nodes"]
        reasoning = [n for n in nodes if "/" in n]
        print(f"{key}: {len(reasoning)} reasoning ledger steps -> {reasoning[:8]}...")

    return outputs


def main() -> None:
    try:
        run_patterns_demo()
    except (RuntimeError, AssertionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
