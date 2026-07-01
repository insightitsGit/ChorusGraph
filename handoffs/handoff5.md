# Handoff 5 — Memory: the agent remembers (Checkpointer + Cortex)

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/DESIGN_v0.2.md`](../docs/DESIGN_v0.2.md) §5.3 (checkpointer), §13 (Cortex), §13.3 (automatic memory policy).
**Builds on:** Handoff 4 (the finance agent is already conversation-state-aware).
**Return in:** `handoffs/handoffback5.md`.

Grounded against the real PrismCortex code (`engine.py`, `adapters/prism.py`) — use the facts in §5, don't re-derive them.

---

## 0. Operating rules
No fakes — real `prismcortex` (`prism_memory()`), real Gemini, real prismlang/prismcache. **Function-first:
prove the agent REMEMBERS. NO performance / latency / cost / traffic measurement** (A/B benchmark later).

## 1. Goal

The finance agent **remembers** — two complementary forms (both headlines):
1. **Durably within a thread** — conversation state survives a restart (PrismCheckpointer).
2. **Across sessions** — a fact stated in one session is recalled in a new session, with provenance (Cortex).

Function-first: "it remembers, correctly," nothing about speed or cost.

## 2. Deliverables (scope)

### 2.1 PrismCheckpointer — `chorusgraph/checkpoint/`
Persist graph state (the H4 `conversation_history` + sections + graph position) via LangGraph's
checkpointer interface. Backend: **SQLite for local, Postgres option** (same interface). Demo: run a
2-turn conversation, drop the process, resume the thread by `thread_id` — state intact, turn 3
continues the conversation.

### 2.2 Cortex long-term memory — `chorusgraph/memory/`
Wire **`prism_memory()`** (real stack — see §5) as the L3 memory service for the finance agent:
- **Auto-digest each turn, ASYNC and salience-gated.** Digest runs *after* the response ships (off the
  turn's critical path, §13.3). `digest()` is already salience-gated (`SKIP_BANDS` skip the LLM) — rely
  on that, don't re-implement it.
- **Recall into the controller.** Before drafting, `recall()` relevant facts and inject them (budgeted)
  into the writer prompt. `recall()` returns `answer`, `confidence`, `freshness` — surface these.
- Demo: **session 1** — user states a durable preference ("my risk tolerance is conservative");
  **session 2 (new thread)** — the agent recalls it and tailors the answer, and `explain()`/evidence
  shows the provenance.

### 2.3 Wire memory confidence into the ledger (light)
Populate the ledger's `grounding_score`/confidence slots from Cortex `recall().confidence` when memory
is used — this is the belief-signal foundation for §7.5, cheap to add here.

## 3. Grounded facts (from the real Cortex code — use these)
- **Factory:** `from prismcortex.adapters.prism import prism_memory` → real PrismLang (k=128) + Resonance
  + PrismLib cache + Gemini. Needs `prismcortex[prism,gemini]` + a key.
- **`digest(text, source_id, agent_id)`** → salience-assessed; low-salience skipped (no LLM); idempotent
  on identical input; uncertain facts staged for `sleep()`.
- **`sleep()`** = consolidation pass (drain staging, resolve conflicts). Run it **async / on idle**, not inline.
- **`recall(query)`** → `RecallResult(answer, cache_hit, confidence, freshness, subgraph_hash, ...)`.
- **`explain(query)`** → evidence trail (provenance) for the "prove it" demo.
- **KNOWN CONSTRAINT (state it, don't trip on it):** the GraphStore is `InMemoryGraphStore` — Cortex
  remembers across sessions **while its process/service stays up**, but the knowledge graph is **not
  durable across a restart** (the answer cache is SQLite-durable; the graph is RAM). For H5, run Cortex
  as a persistent in-process/service memory so cross-session recall works; **durable-across-restart
  GraphStore is a separate future item — flag it, don't build it here.** (The checkpointer covers
  *conversation-state* durability; Cortex durability is the open piece.)

## 4. Explicitly OUT of scope
Performance / latency / cost / traffic / FP measurement (A/B later) · execution patterns ReAct/Reflection/Plan-Solve (H6) · durable-across-restart Cortex GraphStore · live cache serving · native engine/DSL.

## 5. Acceptance criteria
- [ ] A thread **resumes from checkpoint** after a process restart with conversation state intact.
- [ ] A fact stated in **session 1 is recalled in session 2** (new thread), with provenance via `explain()`.
- [ ] Auto-digest runs **async** (does not add latency to the turn) and is **salience-gated** (trivial turns skipped).
- [ ] Ledger confidence/grounding slot populated from Cortex `recall().confidence` when memory is used.
- [ ] Real `prismcortex`/Gemini — no mocks; `pytest` green.
- [ ] **No performance numbers reported** — functional milestone.

## 6. Scope-management note
If §2.1 (checkpointer) + §2.2 (Cortex) is too large for one clean handoff, **ship the checkpointer
first, flag Cortex as H5b, and say so** — don't cram both in badly. Both are the memory headline; either
order is fine as long as each is done properly.

## 7. Open questions for handoffback5
1. Checkpointer backend you used (SQLite/Postgres) and how it hooks LangGraph's checkpointer interface.
2. How you scheduled the async digest (background thread / task) so it stays off the response path.
3. Did cross-session recall work with the in-memory GraphStore running as a persistent service? Any surprises?
4. Is durable-across-restart Cortex memory needed for the first release, or can it wait? Your read.
5. Proposed H6 scope (execution patterns).

## 8. Return format
Same as prior: summary · file tree · how to run · real run output (paste a cross-session recall + a
thread resume) · decisions/deviations · blockers · answers to §7 · design contradictions · proposed H6 scope.

---
*Handoff 5 · architect: Claude · grounded in real Cortex code · function-first · the agent remembers · NO perf measurement.*
