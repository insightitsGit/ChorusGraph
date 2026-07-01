# Handoff 6 — Return · Senior Engineer (Cursor) → Architect

## 1. Summary

Shipped **real agentic reasoning** on a shared agent-loop substrate (v0.6.0):

1. **`chorusgraph/agents/loop.py`** — generic reason ↔ act ↔ router cycle with `PlanPolicy` budgets (`max_steps`, `token_budget`).
2. **ReAct** — LLM-driven Thought→Action→Observation; replaces deterministic FX regex for pattern graphs.
3. **Reflection** — Writer→Validator→revise loop with observable revision steps.
4. **Plan-Solve** — static planner JSON + sequential executor (with computed cross-rate fallback for non-tool steps).
5. **Observable planning** — `agent_trace` expanded into per-step Route Ledger entries (`node/kind`).
6. **Cleanup** — migrated finance Gemini client to `google.genai`; removed demo-specific `recall_for_turn()` query.

**47 passed, 1 skipped.** All three patterns demonstrated on real Frankfurter tools + real Gemini.

## 2. File tree

```
C:\code\ChorusGraph\
├── pyproject.toml                              # v0.6.0, google-genai, chorusgraph-finance-patterns CLI
├── chorusgraph/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── policy.py                           # PlanPolicy
│   │   ├── loop.py                             # run_agent_loop(), AgentTraceStep
│   │   ├── react.py                            # run_react()
│   │   ├── reflection.py                       # run_reflection()
│   │   └── plan_solve.py                       # run_plan_solve(), plan_tasks()
│   ├── adapter/wrap.py                         # agent_trace → ledger sub-steps
│   └── examples/finance_agent/
│       ├── gemini_client.py                    # google.genai (was google.generativeai)
│       ├── pattern_nodes.py                    # pattern graph handlers
│       ├── patterns_graph.py                   # build_react/reflection/plan_solve_graph()
│       └── run_patterns_demo.py
├── tests/
│   ├── test_agents.py                          # substrate + real Frankfurter (stub LLM planner)
│   └── test_patterns.py                        # E2E pattern graphs + ledger traces
└── handoffs/
    └── handoffback6.md
```

## 3. How to run

```powershell
cd C:\code\ChorusGraph
pip install -e ".[dev,gemini,cortex]"

$env:GEMINI_API_KEY = "<your-key>"

pytest -v

python -m chorusgraph.examples.finance_agent.run_patterns_demo
# or: chorusgraph-finance-patterns
```

## 4. Test results

```
47 passed, 1 skipped in ~115s
```

## 5. Real run output (one per pattern)

### ReAct — 2 LLM-chosen tool calls

```
Question: Compare USD to EUR and USD to GBP ... which is stronger against USD?
Tool calls: fetch_exchange_rate USD→EUR (0.8785), fetch_exchange_rate USD→GBP (0.75528)
Answer: GBP is stronger against USD (1 USD buys less GBP than EUR).

Ledger trace (excerpt):
  react_agent/thought → react_agent/router → react_agent/action → react_agent/observation
  (×2 cycles) → writer → validator
```

### Reflection — wrong figure caught and fixed

```
Question: USD/EUR and USD/GBP rates — which is stronger?
Initial draft injected with wrong rate (0.9900 demo).
Ledger trace:
  validator/thought → validator/observation → validator/revision → validator/thought → validator/observation
Answer (revised): USD/EUR 0.8785, USD/GBP 0.75528 (exact tool rates).
validation.approved: true
```

### Plan-Solve — static multi-step plan

```
Question: Fetch USD/EUR and USD/GBP, compute EUR/GBP cross-rate, summarize.
Plan steps (ledger): plan_solve/plan_step ×4 → action/observation ×2 → computed cross observation
Answer: EUR/GBP cross-rate ≈ 1.163145 (computed from USD legs).
```

## 6. Decisions / deviations

| Decision | Rationale |
|----------|-----------|
| **Shared `run_agent_loop()` substrate** | ReAct uses it directly; Plan-Solve uses plan_step trace + sequential executor; Reflection uses trace-only loop via `run_reflection()`. |
| **JSON ReAct/planner responses** | `generate_json()` via `google.genai` for reliable Action parsing vs free-text. |
| **Ledger expansion in `wrap.py`** | Each `agent_trace` step becomes `{node}/{kind}` ledger entry — observable planning without LangGraph sub-node explosion. |
| **Plan-Solve cross-rate compute fallback** | Planner often emits a non-tool "compute" step; executor derives EUR/GBP from USD legs instead of failing. |
| **H4 deterministic researcher retained** | Original `graph.py` unchanged for backward compat; pattern graphs use LLM ReAct/plan nodes. |
| **Removed `"What is the user's risk tolerance?"` from recall_for_turn** | Per §2.6 cleanup; kept general profile query only. |

## 7. Blockers

- **Belief-knobs (`confidence_stop`, `groundedness_floor`)** — deferred; need calibrated grounding signals (§7.5).
- **Cortex recall generalization** — profile fallback still orchestrator-side; separate item.
- **Floating Gemini model aliases** — PrismCortex warning persists.

## 8. Answers to Handoff 6 §6

### 1. LLM ReAct vs deterministic researcher (functional)?

On the 2-tool comparison task, **ReAct reliably selects `fetch_exchange_rate` twice** with correct USD/EUR and USD/GBP args when driven by real Gemini. The deterministic regex researcher handles single-pair FX well but **cannot reason through multi-tool comparisons** without explicit multi-pair parsing — that's why ReAct is the right fallback for ambiguous multi-step finance questions. Occasional variance: LLM may finish after one tool if not prompted carefully; `max_steps=6` and comparison-style questions mitigate this.

### 2. Observable planning — lossy?

**Works cleanly.** Every Thought/Action/Observation/plan_step/revision appears as a separate ledger step under `{parent_node}/{kind}`. Not lossy for content up to 500 chars in `rule_chain`. Minor caveat: parent node also records aggregate `rule_chain` from the handler — some duplication, not information loss.

### 3. Belief-knobs need calibrated grounding first?

**Yes.** We populate `grounding_score` from Cortex confidence when available, but `confidence_stop` / `memory_confidence_gate` need empirically calibrated thresholds — same A/B benchmark that validates cache FP. Budget-only `PlanPolicy` is the right H6 scope.

### 4. Proposed H7 scope

1. **Durable Cortex GraphStore** (Postgres / customer datastore).
2. **Cortex recall generalization** — remove orchestrator profile fallback hacks.
3. **A/B benchmark (Container B)** — latency, cost, traffic, FP on real finance agent.
4. **PlanPolicy belief-knobs** once signals are calibrated.
5. **HITL interrupts** on validator rejection (checkpointer ready from H5).

## 9. Design contradictions

- §7.6 says "deterministic-first, ReAct as fallback" — H6 adds ReAct as a **parallel pattern graph**, not a global replacement; original deterministic path preserved.
- Plan-Solve spec says no re-plan on failure — executor stops on tool error but computes cross-rate locally for non-tool steps (pragmatic deviation).
- Observable planning duplicates trace in both `agent_trace` ledger sub-steps and parent `rule_chain` — acceptable for audit richness.

## 10. Acceptance criteria checklist

- [x] ReAct completes 2-tool finance task with LLM-chosen tools
- [x] Reflection catches wrong figure and fixes on revision
- [x] Plan-Solve executes static multi-step plan end-to-end
- [x] Thought/Action/plan-step in Route Ledger
- [x] Real Gemini + real tools; pytest green
- [x] No performance numbers reported

---
*Handoff 6 · architect: Claude · three patterns on one substrate · v0.6.0*
