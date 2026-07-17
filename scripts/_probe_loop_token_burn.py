"""Evidence script for loop token-burn findings (not a permanent test)."""

from __future__ import annotations

import json

from chorusgraph.agents import Agent, PlanPolicy, ReActOpts
from chorusgraph.nodes.tool import default_finance_registry


def _llm_factory(make_payload):
    call = {"n": 0}

    def llm(_s: str, _u: str) -> str:
        call["n"] += 1
        return json.dumps(make_payload(call["n"]))

    return llm, call


def main() -> None:
    reg = default_finance_registry()

    # A: identical tool+args, stop_on_repeated_action=False (opt-out of default)
    llm, call = _llm_factory(
        lambda n: {
            "thought": f"unique thought {n}",
            "action": {
                "tool": "fetch_exchange_rate",
                "args": {"from_currency": "USD", "to_currency": "EUR"},
            },
            "finish": False,
        }
    )
    r = Agent(
        pattern="react",
        tools=reg,
        model=llm,
        policy=PlanPolicy(max_steps=6),
        pattern_opts=ReActOpts(max_tool_calls=10, stop_on_repeated_action=False),
    ).run("USD EUR")
    print(
        "A repeated_action=False:",
        f"tools={len(r.tool_calls)} finish={r.finish_reason} llm={call['n']}",
    )

    # B: same payloads, stop_on_repeated_action=True
    llm, call = _llm_factory(
        lambda n: {
            "thought": f"unique thought {n}",
            "action": {
                "tool": "fetch_exchange_rate",
                "args": {"from_currency": "USD", "to_currency": "EUR"},
            },
            "finish": False,
        }
    )
    r = Agent(
        pattern="react",
        tools=reg,
        model=llm,
        policy=PlanPolicy(max_steps=6),
        pattern_opts=ReActOpts(max_tool_calls=10, stop_on_repeated_action=True),
    ).run("USD EUR")
    print(
        "B repeated_action=True:",
        f"tools={len(r.tool_calls)} finish={r.finish_reason} llm={call['n']}",
    )

    # C: alternating two arg sets — second occurrence of EUR trips repeated_action
    llm, call = _llm_factory(
        lambda n: {
            "thought": f"self-heal plan v{n}",
            "action": {
                "tool": "fetch_exchange_rate",
                "args": {
                    "from_currency": "USD",
                    "to_currency": "GBP" if n % 2 else "EUR",
                },
            },
            "finish": False,
        }
    )
    r = Agent(
        pattern="react",
        tools=reg,
        model=llm,
        policy=PlanPolicy(max_steps=5, token_budget=100_000),
        pattern_opts=ReActOpts(max_tool_calls=20, stop_on_repeated_action=True),
    ).run("fix rates")
    print(
        "C unique alternating args:",
        f"tools={len(r.tool_calls)} finish={r.finish_reason} llm={call['n']}",
    )

    # C2: never-repeating action signatures (TokenShield-style unique self-heal)
    llm, call = _llm_factory(
        lambda n: {
            "thought": f"self-heal attempt {n} with novel probe",
            "action": {
                "tool": "compound_interest",
                "args": {
                    "principal": 1000.0 + n,
                    "annual_rate_pct": 5.0,
                    "years": 1.0,
                },
            },
            "finish": False,
        }
    )
    r = Agent(
        pattern="react",
        tools=reg,
        model=llm,
        policy=PlanPolicy(max_steps=8, token_budget=8000),
        pattern_opts=ReActOpts(max_tool_calls=20, stop_on_repeated_action=True),
    ).run("heal portfolio")
    print(
        "C2 never-repeat unique args:",
        f"tools={len(r.tool_calls)} finish={r.finish_reason} llm={call['n']}",
        "(expect max_steps — repeated_action cannot fire)",
    )

    # D: crude token_budget rarely binds before max_steps
    llm, call = _llm_factory(
        lambda n: {
            "thought": "x" * 20,
            "action": {
                "tool": "fetch_exchange_rate",
                "args": {"from_currency": "USD", "to_currency": "EUR"},
            },
            "finish": False,
        }
    )
    r = Agent(
        pattern="react",
        tools=reg,
        model=llm,
        policy=PlanPolicy(max_steps=8, token_budget=8000),
        pattern_opts=ReActOpts(max_tool_calls=20, stop_on_repeated_action=False),
    ).run("budget check")
    print(
        "D default budgets:",
        f"tools={len(r.tool_calls)} finish={r.finish_reason} llm={call['n']}",
        "(expect max_steps — token_budget does not bind on short JSON replies)",
    )


if __name__ == "__main__":
    main()
