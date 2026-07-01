# Handoff 7 — Return · Senior Engineer (Cursor) → Architect

## 1. Summary

Shipped **unified `Agent` type + configurable NOW knobs + LATER belief stubs** (v0.7.0):

1. **`Agent(pattern, tools, model, role, policy, pattern_opts, belief).run(...)`** — one entry point; pattern selected via pluggable strategy registry (no monolithic `if pattern == …`).
2. **Strategies** — `ReactStrategy`, `ReflectionStrategy`, `PlanSolveStrategy` under `chorusgraph/agents/strategies/`.
3. **Extended `PlanPolicy`** — `on_exhaust`, `trace_level`; per-pattern opts dataclasses with H6-compatible defaults.
4. **NOW knobs active + tested** — `stop_on_repeated_action`, `require_tool_before_finish`, `max_revisions`, `on_step_failure="skip"`, etc.
5. **`BeliefPolicy` stub** — any non-None knob raises `BeliefPolicyNotCalibratedError` at `run()` time.
6. **`AgentNode`** — Agent IS-A Node; ReAct and Plan-Solve finance pattern handlers use `AgentNode(agent, …)`.
7. **H6 shims preserved** — `run_react`, `run_reflection`, `run_plan_solve` delegate to `Agent`; existing tests green.

**53 passed, 1 skipped.** Real Gemini E2E via finance pattern graphs (ReAct runs as `AgentNode`).

## 2. File tree

```
C:\code\ChorusGraph\
├── pyproject.toml                              # v0.7.0
├── chorusgraph/
│   ├── __init__.py                             # v0.7.0
│   └── agents/
│       ├── __init__.py                         # exports Agent, AgentNode, opts, shims
│       ├── agent.py                            # unified Agent type
│       ├── agent_node.py                       # AgentNode, promote_to_agent, agent_result_to_state
│       ├── policy.py                           # PlanPolicy, ReActOpts, ReflectionOpts, PlanSolveOpts, BeliefPolicy
│       ├── loop.py                             # run_agent_loop (+ "continue" route for require_tool_before_finish)
│       ├── plan_utils.py                       # PlanStep, plan_tasks, _try_compute_cross (import-safe)
│       ├── react_utils.py                      # parse_react_json, tool_catalog (import-safe)
│       ├── react.py                            # run_react shim → Agent
│       ├── reflection.py                       # run_reflection shim → Agent
│       ├── plan_solve.py                       # run_plan_solve shim → Agent
│       └── strategies/
│           ├── __init__.py                     # STRATEGY_REGISTRY, get_strategy()
│           ├── base.py                         # AgentContext, AgentRunResult, AgentStrategy protocol
│           ├── react_strategy.py
│           ├── reflection_strategy.py
│           └── plan_solve_strategy.py
│   └── examples/finance_agent/
│       └── pattern_nodes.py                    # make_react_agent_handler → Agent + AgentNode
├── tests/
│   └── test_agent.py                           # belief stubs + knob tests + shim parity
└── handoffs/
    └── handoffback7.md
```

## 3. How to run

```powershell
cd C:\code\ChorusGraph
pip install -e ".[dev,gemini,cortex]"

$env:GEMINI_API_KEY = "<your-key>"

pytest -v

# All three patterns via AgentNode-backed finance graphs
python -m chorusgraph.examples.finance_agent.run_patterns_demo

# Direct Agent API (ReAct example)
python -c "
from chorusgraph.agents import Agent, PlanPolicy, ReActOpts
from chorusgraph.examples.finance_agent.gemini_client import GeminiClient
from chorusgraph.nodes.tool import default_finance_registry
gemini = GeminiClient()
agent = Agent(
    pattern='react',
    tools=default_finance_registry(),
    model=gemini.generate_json,
    policy=PlanPolicy(max_steps=6),
    pattern_opts=ReActOpts(max_tool_calls=6),
)
r = agent.run('Compare USD/EUR and USD/GBP — which is stronger against USD?')
print('tool_calls:', [t['tool'] for t in r.tool_calls])
print('finished:', r.finished, r.finish_reason)
"
```

## 4. Test results

```
53 passed, 1 skipped in ~86s
```

New knob tests (`tests/test_agent.py`):

| Test | Knob proven |
|------|-------------|
| `test_stop_on_repeated_action_breaks_loop` | Same tool+args twice → `finish_reason=repeated_action`, 1 tool call |
| `test_require_tool_before_finish_blocks_early_finish` | Early finish blocked → forced tool call first |
| `test_max_revisions_caps_reflection` | `max_revisions=2` → exactly 2 passes |
| `test_plan_solve_skip_on_step_failure` | Bad step skipped → step 2 succeeds, `failed_step=None` |
| `test_belief_policy_raises_when_enabled` | `BeliefPolicy(confidence_stop=0.9)` → `BeliefPolicyNotCalibratedError` |
| `test_agent_run_react_matches_run_react_shim` | Shim parity with unified Agent |

## 5. Real run output

### ReAct via `AgentNode` in finance graph (real Gemini + Frankfurter)

```
Question: Compare USD to EUR and USD to GBP exchange rates and tell me which currency is stronger against USD.
Tool calls: 2
  - fetch_exchange_rate ok=True USD→EUR rate=0.8785
  - fetch_exchange_rate ok=True USD→GBP rate=0.75528
Ledger path: cache_gate -> react_agent -> react_agent/thought -> react_agent/router ->
             react_agent/action -> react_agent/observation (×2) -> writer -> validator
```

(`make_react_agent_handler` builds `Agent(pattern="react", …)` wrapped in `AgentNode(node_id="react_agent")`.)

### Knob demo — `stop_on_repeated_action` (stub LLM, deterministic)

```
Agent(pattern="react", pattern_opts=ReActOpts(stop_on_repeated_action=True))
→ finish_reason='repeated_action'
→ tool_calls: 1 (loop broken after duplicate fetch_exchange_rate USD/EUR)
```

### Plan-Solve + Reflection + Plan-Solve graphs

All three pattern demos pass via `run_patterns_demo` with real Gemini (same rates as H6).

## 6. Decisions / deviations

| Decision | Rationale |
|----------|-----------|
| **Pluggable strategy registry** | Satisfies §2.1 "no monolith"; each pattern is a class with `run(ctx)`. |
| **Helpers split to `react_utils.py` / `plan_utils.py`** | Breaks circular imports (strategy → shim → Agent → strategy). Shims lazy-import `Agent`. |
| **H6 defaults preserved** | `stop_on_repeated_action=False`, `require_tool_before_finish=False`, `on_step_failure="abort"` — zero-config behavior unchanged. |
| **`failed_step` only on abort** | With `on_step_failure="skip"`, execution continues and `failed_step` stays `None` at success. |
| **`loop.py` "continue" route** | When `require_tool_before_finish` blocks finish, router returns `"continue"` instead of stopping. |
| **`BeliefPolicy.assert_disabled()` in every strategy** | Fail-fast before any pattern runs if LATER knobs enabled. |
| **Deferred full behavior for some knobs** | See §7 below. |

## 7. Deferred knobs (scope management)

Shipped API + defaults; **behavior stubbed or metadata-only**:

| Knob | Status |
|------|--------|
| `critic_model` | Accepted in `ReflectionOpts`; not wired to alternate model (uses Agent's `model`). |
| `evaluator` (`llm_critique` / `run_tests` / `grounding_guard`) | Recorded in trace metadata; validate/revise callbacks drive behavior. |
| `replan_on_failure` | Only triggers when `on_step_failure="replan"` AND flag true; replan re-calls planner LLM. |
| `checkpoint_after_step` | Adds router trace entries; no durable checkpoint persistence (H5 checkpointer not hooked here). |
| `on_exhaust` / `trace_level` | On `PlanPolicy`; `trace_level` not yet filtering trace emission (default `normal` = full trace). |
| All `BeliefPolicy` fields | Raise if non-None. |

## 8. Blockers resolved

- **Circular import** (`agent → strategies → react.py → agent`) — fixed by extracting `react_utils.py` / `plan_utils.py` and lazy-importing `Agent` in shims.

## 9. Answers to Handoff 7 §6

### 1. Did any pattern resist the unified strategy interface?

**Reflection** was the outlier — it doesn't use `run_agent_loop()` (generate → validate → revise is callback-driven, not tool-loop). It maps cleanly as a standalone strategy implementing `AgentStrategy.run(ctx)` with `validate`/`revise` injected via `Agent.run(..., validate=, revise=)`. ReAct uses the loop substrate; Plan-Solve uses its own planner + sequential executor. **No pattern blocked unification.**

### 2. Did any NOW knob's default silently change H6 behavior?

**No.** Defaults match H6: repeated-action loop allowed, finish without tool allowed, reflection max 3 passes, plan abort on failure. Verified by all pre-H7 tests (`test_agents.py`, `test_patterns.py`) still green without config changes.

### 3. Proposed H8 scope

1. **Durable Cortex GraphStore** (Postgres-backed L3, customer datastore).
2. **A/B benchmark (Container B)** — latency, cost, traffic, FP on real finance agent; calibrate belief-tier thresholds.
3. **Enable `BeliefPolicy` knobs** once grounding/confidence signals are calibrated (§7.5).
4. **Wire deferred NOW knobs** — `critic_model`, `on_exhaust` behavior, durable `checkpoint_after_step` via H5 checkpointer.
5. **Cortex recall generalization** — remove orchestrator profile fallback hacks.

## 10. Design contradictions

- §7.8 "Agent IS-A Node" — implemented as composition (`AgentNode` wraps `Agent` handler) rather than inheritance; functionally equivalent for graph wiring.
- `evaluator` enum suggests multiple critique backends but Reflection still requires injectable `validate`/`revise` — enum is forward-compatible metadata until H8 wires LLM critic.
- Plan-Solve `on_step_failure="skip"` records failed tool call in `tool_calls` with `ok=False` but does not set `failed_step` — intentional: skip means "continue plan", not "abort run".

## 11. Acceptance criteria checklist

- [x] All three patterns run via `Agent(pattern=…)` with H6-identical default behavior
- [x] NOW knobs tested: `stop_on_repeated_action`, `require_tool_before_finish`, `max_revisions`, `on_step_failure="skip"`
- [x] LATER belief knobs disabled (`BeliefPolicyNotCalibratedError`)
- [x] ReAct runs as `AgentNode` in finance graph
- [x] Real Gemini E2E; pytest green; no perf numbers

---
*Handoff 7 · architect: Claude · unified Agent type · NOW knobs + LATER stubs · v0.7.0*
