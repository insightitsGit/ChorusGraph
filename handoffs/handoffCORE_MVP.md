# Handoff CORE-MVP — ChorusGraph Execution Engine (complete MVP, engine-first)

**Director:** Amin · **Architect:** Claude · **Engineer:** Cursor
**Spec:** [`docs/ENGINE_DESIGN_v0.1.md`](../docs/ENGINE_DESIGN_v0.1.md) (architecture) — this handoff is the executable plan.
**Date issued:** 2026-07-02

---

## 0. The mandate (one line)

Build the ChorusGraph **execution engine** so ChorusGraph **replaces** LangGraph — it does not run on it.
The **complete MVP** is a graph you can author, run, checkpoint/resume, stream, and interrupt (HITL),
with role agents + multi-agent + cache-skip + native trace, all over **Prism-native communication**
(PrismLang envelopes on the Resonance bus), plus one migrated real example and an honest re-benchmark.

**The replacement test (CI-enforced):** `grep -rn "langgraph" chorusgraph/core/` → **0 matches.**

---

## 1. Non-negotiables (these are repeated Director asks — encode them, do not re-litigate)

1. **MVP-first, and the MVP must be COMPLETE** — end-to-end usable, not a partial layer. Ship the whole
   vertical (author→run→persist→resume→stream→interrupt→observe) before polishing any single part.
2. **Deterministic-first — NO gratuitous LLM calls.** Cache interceptor + deterministic routing run
   **before** any LLM node. A node must not call the LLM if a cache hit or a deterministic rule answers.
   One LLM call where one is needed; **zero** where none is.
3. **Communication is Prism-native, always.** Every node→node message is a `PrismEnvelope` on the
   **Resonance bus** (`InProcessBroadcast`). Cross-machine = **CHORUS**. Cross-container = **PrismAPI**.
   **Never a raw dict handed between nodes.**
4. **No mocks / no fakes.** Real Gemini via the dedicated `GEMINI_API_KEY`. Recorded fixtures are OK;
   fabricated numbers are never OK. `.gitignore` keeps `.env` / secrets / `*.db` / caches out of git.
5. **Fairness is sacred.** Any benchmark varies **only the framework**; the baseline is competent; every
   threshold is **measured**, never tuned to win.
6. **Commit/push only when the Director asks.** Commit trailer:
   `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
7. **Every task deletes a LangGraph debt** (§7). No task is "done" if it adds a new bolt-on.

---

## 2. Why this handoff exists (context — read once)

The prior design borrowed `langgraph.graph.StateGraph` (engine) and wrapped `langgraph.checkpoint`
(persistence), making ChorusGraph a **layer on LangGraph** — the opposite of the goal. Survey of the
real repo shows **the only missing component is the scheduler**; every other engine part already exists
Prism-native and was merely wired to LangGraph. This handoff builds that scheduler and rewires the
existing parts onto it.

---

## 3. Real assets to build ON (grounded — confirm exact signatures against the installed libs first)

| Concern | Use this real asset | Where |
|---|---|---|
| Message / channel value | `prismlang.PrismEnvelope` (`turn_id, agent_id, category_slug, vector, rule_chain`) | prismlang |
| Bus (in-proc) / distributed | `prismresonance.InProcessBroadcast` / `RedisBroadcast` — `register_agent`/`set_frequency`/`broadcast`/`dominant_frequency` | prismresonance |
| Semantic routing / search | `prismresonance.ResonanceEngine`, priority bands `EMERGENCY..ARCHIVE` | prismresonance |
| Checkpoint / persistence / time-travel | `prismlang.AsyncPostgresCheckpointer` (`aput`,`aput_writes`,`aget_tuple`,`alist`,`aget_delta_channel_history`,`aprune`,`acopy_thread`); `AsyncJsonFileCheckpointer` for local | prismlang |
| Cross-boundary re-projection | `prismlang.BoundaryTranslator.translate` | prismlang |
| Cross-machine transport (CHORUS mesh) | `prism.cluster.transport` (+ `node`, `cache`, `health`, `alerts`) | prismlib-plus |
| Cross-container federation (PrismAPI) | `prism.api` (`provider`, `consumer`, `auth`, `schema`, `mcp`, `multi_provider`); `prism.bridge.vector` for boundary re-projection | prismlib-plus |
| Semantic cache / skip | `chorusgraph.cache_gate.gate(msg, Section, cache, sidecar, coarse_threshold, verify_threshold, raw_embedding_384, projected_vector_64)`; `CachePolicy` | chorusgraph |
| Long-term memory | `chorusgraph.memory.cortex_service` (`recall`, `digest`, `explain`, bitemporal) | chorusgraph |
| Native trace | `chorusgraph.ledger` — `RouteLedger`, `LedgerStep(node, edge_taken, rule_chain, duration_ms, cache_hit, cache_score, grounding_score)` | chorusgraph |
| Role nodes | `chorusgraph.nodes.roles` — `RoleTemplate`, `Node.with_role`, `ResearcherNode/WriterNode/ValidatorNode`, `promote` | chorusgraph |
| Tool node | `chorusgraph.nodes.tool` | chorusgraph |
| Agent patterns | `chorusgraph.agents` — `run_react`, `run_reflection`, `run_plan_solve`, `run_agent_loop` | chorusgraph |
| Embed→project | `chorusgraph.transforms.projector` — `project_text`, `project_from_raw`, `raw_from_state`, `vector_64_from_state` | chorusgraph |
| Belief knobs | `chorusgraph.sections` / `chorusgraph.policy` (`PlanPolicy`: `confidence_stop`, `groundedness_floor`) | chorusgraph |

> **Engineer:** for every symbol above, run a 2-line import + `dir()` / `inspect.signature` check before
> coding against it. Do not assume a signature. If a symbol's shape differs from this table, **flag it in
> the return** rather than working around it silently.

---

## 4. The COMPLETE MVP = Phases P1–P4 (single runtime, fully working replacement)

This is the "complete MVP" boundary: after P4, a developer can build and run a real agent graph on
ChorusGraph with **zero LangGraph**, including persistence, HITL, streaming, role/multi-agent, cache-skip,
and native observability. P5–P7 (§5) extend it to distributed/federated and prove it on a benchmark —
they are **scheduled in this same handoff, not missing**.

### P1 — Engine core (`chorusgraph/core/`) — CRITICAL PATH
**Build:**
- `chorusgraph/core/graph.py` — the DSL: `Graph(state_schema)`, `add_node`, `add_role_node`,
  `add_edge`, `add_conditional_edges`, `set_entry`, `compile()`. Public re-exports: `chorusgraph.Graph`,
  `START`, `END`. **Mirror LangGraph's method names** so migration is an import swap.
- `chorusgraph/core/channels.py` — envelope channels + reducers. State fields are `Annotated[T, reducer]`
  (support `operator.add`-style reducers). Channel values are carried as `PrismEnvelope`s.
- `chorusgraph/core/scheduler.py` — the **bulk-synchronous super-step loop** (§3.1 of the design):
  1. `active := {entry}`; each super-step runs all `active` nodes **concurrently** (async).
  2. WRITE phase: apply per-channel reducers in deterministic order; record merge in `rule_chain`.
  3. `broadcast()` merged envelopes on the bus.
  4. `next-active` = static-edge targets ∪ Resonance-excited subscribers (conditional edges).
  5. checkpoint boundary (P2 wires the store; P1 uses in-memory).
  6. stop on empty next-active / END / `recursion_limit`.
- `chorusgraph/core/bus.py` — thin wrapper over `InProcessBroadcast`: `register_agent` per node at
  compile, `set_frequency(node, category_slug)`, `broadcast(envelope)`, resolve next via
  `dominant_frequency`. **This is the only channel mechanism — no dict passing.**
- `CompiledGraph.invoke(input, config)` returning final channel values.

**Deterministic-first:** the scheduler evaluates static edges and the cache interceptor (P4 hook point)
**before** invoking a node body, so a node with a cache hit or a pure-deterministic rule never touches
the LLM.

**Exit criteria:**
- A 3-node graph (deterministic nodes) runs end-to-end via `chorusgraph.Graph`.
- `grep -rn langgraph chorusgraph/core` == 0.
- Unit tests: super-step ordering, parallel fan-out, reducer determinism, cycle (node re-activates),
  recursion-limit stop, Resonance conditional routing.

### P2 — Persistence, resume, time-travel (native)
**Build:**
- `chorusgraph/core/persistence.py` — adapt `prismlang.AsyncPostgresCheckpointer` (and
  `AsyncJsonFileCheckpointer` for local dev) to the scheduler's checkpoint boundary: `aput` +
  `aput_writes` at each super-step; `aget_tuple`/`alist` to resume a `thread_id`.
- `CompiledGraph.get_state` / `update_state` / `get_state_history` backed by
  `aget_delta_channel_history` (time-travel / fork).
- **Delete** `chorusgraph/checkpoint/prism.py`'s LangGraph wrapper; re-point callers.

**Exit criteria:** run→kill→resume from checkpoint continues correctly; time-travel forks a past state;
`langgraph.checkpoint` import removed. Tests: resume-after-crash, fork-from-history, retention `aprune`.

### P3 — HITL interrupts + streaming
**Build:**
- Interrupts as **super-step boundary halts**: `interrupt_before` / `interrupt_after` node flags +
  dynamic `interrupt()` → checkpoint + pending writes + suspend + return control; `invoke(None, thread_id)`
  resumes. `update_state` before resume applies human edits.
- `CompiledGraph.stream(...)` / `astream(...)` with modes `values | updates | messages | debug`,
  emitted from the scheduler/bus (not bolted on).

**Exit criteria:** approve/edit/resume round-trip works; token streaming from an LLM node; `debug` mode
emits super-step + Resonance-routing events. Tests: interrupt→edit→resume; each stream mode.

### P4 — Cache interceptor + native Route Ledger + roles/multi-agent (closes the MVP)
**Build:**
- **Cache-skip as a native node-entry interceptor** (design §5): before running node N (if
  `N.cache_policy != NO_CACHE`), call `cache_gate.gate(...)`; on hit, emit the cached value as N's output
  and **skip execution (0 LLM)**, tagging `cache_hit`/`cache_score` on the `LedgerStep`.
- **Route Ledger native**: scheduler writes a `LedgerStep` per node per super-step directly. **Delete**
  `chorusgraph/adapter/wrap.py` (the "non-invasive LangGraph adapter"); ledger is now built-in.
- **Role + multi-agent on the bus**: `add_role_node` binds a `roles.RoleTemplate`; each role node is a
  Resonance-bus agent tuned to its `category_slug`. Provide a supervisor/handoff example using
  Researcher/Writer/Validator + one pattern (`run_react` or `run_reflection`) as a sub-graph of
  super-steps. Cortex `recall` at ingress, `digest` at egress as native channels.

**Exit criteria (MVP COMPLETE):**
- A cache hit skips the LLM node (assert `llm_calls == 0` on the repeat) — the thing the old C/D bolt-on
  couldn't do natively.
- A multi-agent role graph runs entirely over the in-proc Resonance bus with a native ledger trace.
- `langgraph` appears **nowhere** in `chorusgraph/core`, `chorusgraph/checkpoint`, `chorusgraph/adapter`.

---

## 5. Follow-on phases (scheduled here so nothing is missing)

### P5 — Distribution (multi-machine, same cluster)
`RedisBroadcast` for the bus + **CHORUS** transport for cross-machine envelopes. Scheduler stays
location-transparent. Exit: the same graph runs across 2 processes/machines; envelopes ship as CHORUS
tensors; results identical to single-runtime.

### P6 — Federation (cross-container multi-agent) — **requires adding PrismAPI**
Add the PrismAPI dependency (separate repo — **Director to confirm access**). Cross-container agent
hops go over PrismAPI with `BoundaryTranslator.translate` re-projecting envelopes at the boundary.
Exit: an agent in container A federates to an agent in container B via PrismAPI; §2.4 routing rule
(in-proc → cluster → container) selects the transport automatically.

### P7 — Migration shim + honest re-benchmark
- `chorusgraph.compat.langgraph` — run an existing `StateGraph` definition on the ChorusGraph engine
  (import-swap migration).
- **Re-benchmark** the finance A/B (and healthcare C/D) **on the engine**, real Gemini, measured
  thresholds. The current numbers compare LangGraph vs LangGraph+layer and are void as replacement
  evidence — replace them. Report deltas with confidence intervals; disclose where the baseline is weaker.
- **Fix the D benchmark cache-siloing** while here (cache keyed per `session_id|depth` → 0 hits possible;
  make the semantic cache global like B/F so repeats can hit).

---

## 6. Schedule (Director-adjustable; critical path = the scheduler)

Assumes one engineer (Cursor) starting **2026-07-07**; day counts are working days, not wall-clock.
P1 gates everything; P2/P3/P4 can partially overlap after P1's scheduler is stable.

| Phase | Scope | Est. | Depends on | Target window |
|---|---|---|---|---|
| P1 | Engine core: DSL + channels + scheduler + bus | 8–10 d | — | Jul 07 – Jul 18 |
| P2 | Native persistence / resume / time-travel | 3–4 d | P1 | Jul 21 – Jul 24 |
| P3 | HITL interrupts + streaming | 4–5 d | P1 (P2 for resume) | Jul 24 – Jul 30 |
| P4 | Cache interceptor + native ledger + roles/multi-agent | 4–5 d | P1 | Jul 30 – Aug 05 |
| **MVP** | **P1–P4 complete, zero langgraph, end-to-end** | — | — | **≈ Aug 05** |
| P5 | Distribution (RedisBroadcast + CHORUS) | 4–6 d | P4 | Aug 06 – Aug 13 |
| P6 | Federation (PrismAPI + BoundaryTranslator) | 5–7 d | P5, PrismAPI access | Aug 14 – Aug 22 |
| P7 | Migration shim + honest re-benchmark + D cache fix | 5–7 d | P4 (P5 for distributed bench) | Aug 22 – Sep 01 |

**Milestone gates (Architect reviews each return against real code before the next phase starts):**
G1 after P1 (scheduler runs, 0 langgraph in core) · G2 after P2 · G3 after P3 · **G-MVP after P4** ·
G4 after P5 · G5 after P6 · **G-DONE after P7**.

---

## 7. LangGraph-deletion debt (must reach zero — track every item)

| File | Today | Replace with | Phase |
|---|---|---|---|
| `chorusgraph/checkpoint/prism.py` | wraps `langgraph.checkpoint.{Sqlite,Postgres}Saver` | `prismlang.AsyncPostgresCheckpointer` | P2 |
| `chorusgraph/examples/**/graph.py`, `demo_graph.py` | `langgraph.graph.StateGraph` | `chorusgraph.Graph` | P4→P7 |
| `chorusgraph/adapter/wrap.py` | "non-invasive LangGraph adapter" | native ledger in scheduler | P4 |
| `benchmark/container_b/*`, `benchmark/container_d/*` | `from langgraph.graph import StateGraph` | ChorusGraph engine | P7 |

CI gate: `grep -rn "langgraph" chorusgraph/core/` == 0 from end of P1; extend to `chorusgraph/checkpoint`
(after P2) and `chorusgraph/adapter` (after P4).

---

## 8. Testing & proof requirements (per phase, no exceptions)

- **Unit tests** for every core mechanism (scheduler ordering, reducers, routing, checkpoint, interrupt,
  cache-skip). Deterministic — no live LLM in unit tests (use recorded fixtures).
- **One end-to-end example** graph exercised at each gate.
- **The cache-skip proof**: a test that runs the same input twice and asserts the second run records
  `cache_hit=True` and `llm_calls=0` on the cached node.
- **No fabricated results.** Any benchmark number comes from a real Gemini run (dedicated key) or a
  recorded fixture, and the run metadata is committed alongside it.

---

## 9. Definition of Done (the replacement is earned when ALL hold)

- [ ] `grep -rn langgraph chorusgraph/{core,checkpoint,adapter}` == 0; examples import `chorusgraph.Graph`.
- [ ] Author → run → checkpoint → resume → time-travel → interrupt → stream all run Prism-native.
- [ ] Cache-skip is an engine node-entry behavior (repeat ⇒ 0 LLM calls); Route Ledger is the native trace.
- [ ] Role + multi-agent graph runs over the Resonance bus (in-proc), CHORUS (cross-machine), PrismAPI
      (cross-container) — one graph definition, transport chosen by the §2.4 rule.
- [ ] A real LangGraph graph runs unmodified via `compat.langgraph` on the ChorusGraph engine.
- [ ] A/B + C/D benchmarks re-run on the engine (real Gemini, measured thresholds); D cache-siloing fixed;
      deltas reported with confidence intervals.

---

## 10. Return format (Cursor → `handoffback CORE-MVP`)

For each phase completed, return:
1. **Files added/changed** (paths) and **LangGraph debts deleted** (from §7).
2. **Exit-criteria checklist** with pass/fail and the command output proving each (esp. the
   `grep langgraph` gate and the cache-skip `llm_calls==0` test).
3. **Signature deviations** — any Prism symbol whose real shape differed from §3, and how you handled it.
4. **Anything you could not verify** (e.g., PrismAPI access, CHORUS availability) stated plainly — do not
   paper over a gap.
5. **No commit/push** unless the Director asked; if asked, include the commit hash and confirm the trailer.

---
*CORE-MVP v1 · engine-first · the only net-new build is the L1 scheduler; everything else is rewiring
existing Prism-native parts off LangGraph and onto the engine. MVP = P1–P4 complete; P5–P7 scheduled above.*
