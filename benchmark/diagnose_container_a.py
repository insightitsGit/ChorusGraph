"""H11 — diagnose FL1 FX routing (one task, optional live Gemini)."""

from __future__ import annotations

import argparse
import json
import sys

from benchmark.fl1.graph import build_langgraph_agent, fresh_turn_state, run_task
from benchmark.workload import CANONICAL_QUERIES


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Diagnose FL1 ReAct → tool routing")
    parser.add_argument(
        "--message",
        default=CANONICAL_QUERIES["usd_eur"][0],
        help="FX question to run",
    )
    parser.add_argument("--stub", action="store_true", help="Use stub Gemini (no API)")
    args = parser.parse_args(argv)

    if args.stub:
        from benchmark.shared.stub_gemini import StubGemini

        stub = StubGemini(
            [
                {"thought": "finish early", "action": None, "finish": True},
                {
                    "thought": "fetch",
                    "action": {
                        "tool": "fetch_exchange_rate",
                        "args": {"from_currency": "USD", "to_currency": "EUR"},
                    },
                    "finish": False,
                },
                {"thought": "done", "action": None, "finish": True},
            ],
        )
        compiled, gemini, _ = build_langgraph_agent(gemini=stub)
    else:
        import os

        if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
            from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key

            if not resolve_gemini_api_key():
                print("Error: GEMINI_API_KEY required (or use --stub).", file=sys.stderr)
                raise SystemExit(1)
        compiled, gemini, _ = build_langgraph_agent()

    initial = fresh_turn_state(args.message)
    print("=== Initial turn state ===")
    print(json.dumps({k: initial[k] for k in ("message", "scratchpad", "react_done", "tool_calls")}, indent=2))

    result = run_task(args.message, compiled=compiled, gemini=gemini)
    print("\n=== Result ===")
    print(f"tool_calls: {len(result.get('tool_calls') or [])}")
    print(f"llm_calls: {getattr(result.get('_llm_usage'), 'llm_calls', '?')}")
    print(f"task_success_fields: tool_result={bool(result.get('tool_result'))}")
    print(f"answer: {(result.get('response') or '')[:300]}")
    print(f"rule_chain: {result.get('rule_chain')}")


if __name__ == "__main__":
    main()
