# Handoff 6 — Execution Patterns (ReAct · Reflection · Plan-Solve)

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/DESIGN_v0.2.md`](../docs/DESIGN_v0.2.md) §7.6 (patterns), §7.5 (PlanPolicy), §7.7 (role nodes).
**Builds on:** H4 (roles + tool node) + H5 (memory). **Return in:** `handoffs/handoffback6.md`.

---

## 0. Operating rules
No fakes — real Gemini, real tools/prism. **Function-first: prove each pattern WORKS on a real finance
task. NO performance / latency / cost / traffic measurement** (A/B benchmark, later).

## 1. Goal

Add **real agentic reasoning.** Today the "researcher" is deterministic regex — the agent doesn't think.
This handoff builds the **one agent-loop substrate** and ships the three execution patterns as prebuilt
configs on it (§7.6). Function-first: each pattern demonstrably completes a real finance task.

## 2. Deliverables (scope)

### 2.1 Agent-loop substrate — `chorusgraph/agents/loop.py`
The generic cyclic machinery all three patterns share: `llm` (reason) ↔ `tool` (act) ↔ `router`
(act-or-finish), over the H4 role scaffold. Bounded by `max_steps` + a **minimal `PlanPolicy`**
(budgets only for now — `max_steps`, `token_budget`; the belief-knobs like `confidence_stop` wait for
calibrated signals, §7.5). Every step recorded in the Route Ledger.

### 2.2 ReAct prebuilt — `chorusgraph/agents/react.py`
Thought→Action→Observation loop. The researcher becomes an **LLM-driven** ReAct agent that *decides*
which tool to call (replaces the deterministic FX-regex from H4). Demo: a finance question needing
**2 tool calls** (e.g. "compare USD→EUR and USD→GBP and tell me which is stronger") resolved by the
agent reasoning through both.

### 2.3 Reflection prebuilt — `chorusgraph/agents/reflection.py`
`WriterNode` → `ValidatorNode` → if rejected, revise → re-validate. You're most of the way there
(ValidatorNode exists). Demo: a draft containing a **wrong figure** is caught by the validator and
fixed on the next pass.

### 2.4 Plan-Solve prebuilt — `chorusgraph/agents/plan_solve.py`
A `planner` LLM emits a **static task list** upfront; an execution loop runs step N→N+1 without
re-invoking the planner unless a step fails. Demo: a multi-step task ("fetch two rates, compute the
cross-rate, summarize").

### 2.5 Ledger: observable planning
Every Thought / Action / Observation / plan-step is a ledger step (§7.5). This is the "observable
planning" story — make sure the reasoning trace is actually captured, not just the final answer.

### 2.6 Cleanup (fold in — small)
- Drop the demo-specific `recall_for_turn()` query ("What is the user's risk tolerance?"); keep the
  **general** profile query. (Real Cortex-recall generalization is a separate item — note it, don't fix here.)
- Unify the Gemini SDK on `google.genai` (finance agent still on the deprecated `google.generativeai`).

## 3. Explicitly OUT of scope
`PlanPolicy` belief-knobs beyond budgets (confidence_stop / groundedness_floor — need calibrated
signals) · perf/cost/traffic/FP measurement (A/B) · durable Cortex GraphStore · Cortex recall
generalization (note only) · native engine/DSL · the A/B benchmark itself.

## 4. Acceptance criteria
- [ ] **ReAct** agent completes a 2-tool-call finance task, with the tool choices **decided by the LLM** (not regex).
- [ ] **Reflection** catches a wrong figure and fixes it on revision.
- [ ] **Plan-Solve** executes a static multi-step plan end-to-end.
- [ ] Every reasoning step (Thought/Action/plan-step) appears in the Route Ledger.
- [ ] All three run on the real finance agent with real Gemini; no mocks; `pytest` green.
- [ ] **No performance numbers reported** — functional milestone.

## 5. Scope-management note
If all three don't fit cleanly in one handoff, **ship the substrate + ReAct + Reflection** (they share
machinery and Reflection is nearly done), **flag Plan-Solve for H7, and say so.** Done properly beats crammed.

## 6. Open questions for handoffback6
1. Functional reliability: how does the LLM ReAct researcher compare to the deterministic one on picking the right tool? (Functional observation, not a perf benchmark.)
2. Did observable-planning (full reasoning trace in the ledger) work cleanly, or was anything lossy?
3. Does wiring the belief-knobs (`confidence_stop` etc.) need calibrated grounding first — your read?
4. Proposed H7 scope. (Likely: durable Cortex + Cortex recall generalization + the A/B benchmark.)

## 7. Return format
Same as prior: summary · file tree · how to run · real run output (paste one run per pattern showing
the reasoning trace) · decisions/deviations · blockers · answers to §6 · design contradictions · proposed H7 scope.

---
*Handoff 6 · architect: Claude · real agentic reasoning · three patterns on one substrate · function-first · NO perf measurement.*
