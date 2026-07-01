# Handoff 7 — Unified `Agent` type + configurable properties (now + later)

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/DESIGN_v0.2.md`](../docs/DESIGN_v0.2.md) §7.6, §7.7, **§7.8** (the spec).
**Builds on:** H6 (the three `run_react` / `run_reflection` / `run_plan_solve` functions).
**Return in:** `handoffs/handoffback7.md`.

---

## 0. Operating rules
No fakes — real Gemini for E2E. **This is a behavior-preserving REFACTOR + config layer, not new
capability.** Bar: **all existing H1–H6 tests stay green** (same behavior via the new API) + new tests
for each active knob. **NO performance / cost / A-B measurement.**

## 1. Goal

Collapse the three pattern functions into **one configurable `Agent` type** (pattern as a pluggable
strategy on `run_agent_loop`), expose the **NOW** property set as active config with sane defaults,
define the **LATER** belief-tier as a **stubbed-but-disabled** interface, and make `Agent` a role-typed
Node (`AgentNode`). Per §7.8.

## 2. Deliverables (scope)

### 2.1 `Agent` type — `chorusgraph/agents/agent.py`
`Agent(pattern, tools, model, role, policy, pattern_opts).run(...)`. Internally the three H6 patterns
become **strategy configs** (`reason_fn` + `route_fn` + defaults) selected by `pattern`. Keep the H6
behavior intact — this is a re-home, not a rewrite. Pluggable strategies, **no `if pattern == …` monolith.**

### 2.2 PlanPolicy shared knobs — `chorusgraph/agents/policy.py`
Extend the existing budgets with `on_exhaust` (`best_effort` | `abstain` | `escalate`) and `trace_level`.

### 2.3 Per-pattern NOW knobs (each with a default → zero-config still works)
- **ReAct:** `max_tool_calls`, `require_tool_before_finish`, `stop_on_repeated_action`, `observation_char_limit`
- **Reflection:** `max_revisions`, `critic_model`, `evaluator` (`llm_critique` | `run_tests` | `grounding_guard`), `stop_when_no_improvement`
- **Plan-Solve:** `max_plan_steps`, `replan_on_failure`, `on_step_failure` (`retry` | `skip` | `abort` | `replan`), `checkpoint_after_step`, `validate_plan`

### 2.4 LATER belief-tier — stubbed, disabled, documented
Define the interface for `confidence_stop`, `groundedness_floor`, `memory_confidence_gate`,
`escalation_policy`, `novelty_adaptive_steps` — accepted as config, **no-op / raise-if-enabled**, each
documented "requires A/B-calibrated signals (§7.5); disabled until then." The API surface is complete and
stable now; behavior lands after the A/B.

### 2.5 `AgentNode` — `Agent` IS-A `Node`
An `Agent` is usable as a graph node (§7.7); a plain `Node` is promotable to an `Agent` with a pattern.
Demonstrate one pattern running as an `AgentNode` in the finance graph.

## 3. Explicitly OUT of scope
Enabling any belief-tier behavior (stubs only) · perf / cost / A-B measurement · durable Cortex · Cortex
recall generalization · native engine/DSL · new patterns beyond the three.

## 4. Acceptance criteria
- [ ] All three patterns run via `Agent(pattern=…)` with **behavior identical to H6** (existing tests green).
- [ ] Each NOW knob has a default **and** a test proving it works — e.g.:
  - `stop_on_repeated_action` breaks a same-tool-same-args loop;
  - `require_tool_before_finish` blocks a no-tool finish;
  - `max_revisions` caps Reflection rounds;
  - `on_step_failure="skip"` skips a failing Plan-Solve step.
- [ ] LATER belief knobs accepted as config but **disabled** (no-op or explicit "not calibrated" error), documented.
- [ ] One pattern runs as an `AgentNode` inside the finance graph.
- [ ] Real Gemini for E2E; no mocks; `pytest` green. **No perf numbers.**

## 5. Scope-management note
If the full NOW knob set is too much for one clean handoff, ship the **unification + PlanPolicy shared
knobs + the 2–3 highest-value anti-failure guards per pattern + the LATER stubs**, and flag the remaining
knobs for a follow-up. Done properly beats crammed. Say what you deferred.

## 6. Open questions for handoffback7
1. Did any pattern resist the unified strategy interface? (Reflection is the likely one — generate/critique vs tool-loop.)
2. Did any NOW knob's default silently change H6 behavior? (It must not — flag if so.)
3. Proposed H8 scope. (Likely: **durable Cortex GraphStore + the A/B benchmark** — the point cost/perf finally gets measured.)

## 7. Return format
Same as prior: summary · file tree · how to run · real run output (a pattern via `Agent(...)` + one knob
demonstrably working) · decisions/deviations · blockers · answers to §6 · design contradictions · proposed H8 scope.

---
*Handoff 7 · architect: Claude · one Agent type · NOW knobs active + LATER stubs · behavior-preserving refactor · NO perf.*
