# Handoff 1 — ChorusGraph Runnable Spine (Adapter + Route Ledger)

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/DESIGN_v0.2.md`](../docs/DESIGN_v0.2.md) — read §2, §5, §7, §11, §15, §21, §22 before starting.
**Return your results in:** `handoffs/handoffback1.md` (format at the bottom).

---

## 0. Operating rules (non-negotiable)

1. **No fake implementations.** No mocks, no random/stub data for Prism components. Use the
   *real* `prismlang` package and real graphs. If a step genuinely needs an LLM, use a **real
   Gemini call** — never a fake response. (Keep the demo graph LLM-free where possible so tests
   stay cheap and deterministic; see §4.)
2. **Adapter-first — do not reimplement LangGraph's engine.** Run graphs on LangGraph's own
   runtime. You are *observing* execution, not replacing it.
3. **Do not modify existing hub code** (`InsightitsAIAgent/meeting-scheduler/...`). The adapter
   *wraps*; it never forks.
4. **Stay in scope.** Build only what §3 lists. Do **not** build the cache gate, PrismCheckpointer,
   native DSL, tools, or the scheduler yet — those are later handoffs. If you feel pulled to build
   them, stop and note it in the handoffback instead.
5. **Report reality.** If the design is wrong, awkward, or impossible when it meets code, say so in
   the handoffback. Ground-truth beats politeness.

---

## 1. Goal of this handoff

Establish the **runnable spine**: a `chorusgraph` Python package that can take an existing
*compiled* LangGraph `StateGraph`, execute it **unmodified**, and emit a **durable, queryable
Route Ledger** of everything that happened — every node entered, every conditional edge taken, the
router's `rule_chain` (the *why*) where present, timing, and slots for cache/grounding scores that
later handoffs will fill.

This is the "observability without a LangSmith subscription" foundation (DESIGN §22) and the
prerequisite for measuring cache behavior in Handoff 2.

## 2. Why this slice first (context, don't skip)

The #1 product risk is cache correctness (DESIGN §8). We cannot measure it without first being
able to *observe* a graph run in detail. The Route Ledger is that observation layer. Build it on a
real graph now; instrument the cache against it next.

The turn flow the ledger must capture (steps ①–⑨ + async side-effects) is in
[`../docs/WORKFLOW.md`](../docs/WORKFLOW.md). For Handoff 1 you only observe/record the flow — you do
not build the cache_gate or Cortex steps.

## 3. Deliverables (scope)

### 3.1 Package skeleton — `C:\code\ChorusGraph\chorusgraph\`
- `pyproject.toml` (package name `chorusgraph`, Python 3.10+, standalone package for now — the
  `chorusgraph` vs `prismlib-plus[orchestrator]` namespace is an open director decision; note it,
  don't block on it).
- `chorusgraph/__init__.py` with a version string.
- `tests/` with pytest configured. `pip install -e .` must work.

### 3.2 Route Ledger — `chorusgraph/ledger/`
- A `RouteLedger` data model capturing, per run: `run_id`, `turn_id`, `tenant_id`, `graph_id`,
  and an ordered list of **steps**. Each step: `node`, `edge_taken` (branch chosen, if a
  conditional edge), `rule_chain` (list, when the state exposes one), `duration_ms`, `timestamp`,
  and reserved-nullable fields `cache_hit`, `cache_score`, `grounding_score` (filled later).
- A **pluggable durable sink**. Ship two: `SqliteLedgerSink` (default, zero-config for local dev)
  and a `PostgresLedgerSink` (the production target per DESIGN §5.3). Same interface.
- A query helper: fetch a run's full ledger by `run_id`, and list runs by `graph_id`/`tenant_id`.

### 3.3 Adapter — `chorusgraph/adapter/`
- `wrap(compiled_graph, *, tenant_id, graph_id, sink) -> RunnableWithLedger`.
- It must observe a graph run **non-invasively** — prefer LangGraph's own streaming/debug event
  API (`stream_mode="debug"` / `updates`, or `astream_events`) so it works on *any* compiled graph
  without editing its nodes. Extract node transitions and edge decisions from those events; pull
  `rule_chain` / `prism_sequence` from state when present (the hubs put it there — see
  `website_hub/graph.py` `_prism_audit_node` and PrismLang's envelope).
- Choose the exact mechanism yourself; **report in the handoffback which event API actually
  exposed node+edge transitions reliably**, since that's a known LangGraph rough edge.

### 3.4 Demo + tests (real, no mocks)
- **Primary demo:** a minimal LLM-free example graph (3–4 nodes with one conditional edge) built
  with real `langgraph` + a real `prismlang` `PrismProjector` on the state, wrapped by the adapter,
  producing a ledger. This keeps the core test deterministic and free.
- **Stretch demo (attempt, report if blocked):** wrap the *real* `website_hub` compiled graph
  (`get_graph()`) and produce a ledger for one turn. This proves it works on production code. It
  has heavy deps (Gemini, pgvector) — if you can't stand it up, **document exactly what blocked
  you** rather than faking it.
- **Tests:** assert the ledger records every node on the taken path, the correct branch at the
  conditional edge, and the `rule_chain` when present. Use real components.

### 3.5 (Optional, only if cheap) OpenTelemetry hook
- If trivial, emit each step as an OTel span too (DESIGN §22). If it adds real effort, **skip it**
  and note it as a Handoff-2 candidate. Do not let it expand this slice.

## 4. Explicitly OUT of scope (do not build)
Cache gate / two-stage verify · PrismCheckpointer / persistence / resume · HITL / interrupts ·
native DSL (`Graph`, `SectionSchema`) · tool node · `remote`/PrismAPI node · scheduler / native
engine · MCP client · security hardening. All are later handoffs.

## 5. Acceptance criteria
- [ ] `pip install -e .` succeeds; `pytest` green.
- [ ] Running the primary demo yields a `RouteLedger` whose step count and branch match the path taken.
- [ ] `rule_chain` is captured for at least one router step.
- [ ] Ledger persists to SQLite and is re-queryable by `run_id`; Postgres sink has the same interface (a smoke test is enough).
- [ ] Adapter runs the graph **without modifying it**.
- [ ] No mocks/fakes for Prism components anywhere in the shipped code or tests.

## 6. Open questions to answer in the handoffback
1. Which LangGraph event API reliably exposed node **and** edge-decision transitions? Any that didn't?
2. Did the stretch demo (real `website_hub`) run? If not, precisely what blocked it?
3. Anything in DESIGN §5/§7/§11 that was wrong or awkward against real LangGraph behavior?
4. Your recommendation for the Postgres ledger schema (so I can lock ADR-003).
5. *(Cache-layer confirmation, not built in this slice — just verify while you're in the repos):*
   Does PrismCache use a **real embedder** (SentenceTransformer/MiniLM), and does the silent
   `HashEmbedder` fallback ever trigger? How would you make that fallback fail loudly?
6. *(Same — informational)* What does `ClusterCache` use as its backing/sync store? We need this to
   state cache persistence accurately.

---

## 7. Return format — write `handoffs/handoffback1.md` with:
1. **Summary** — what you built, in 3–5 lines.
2. **File tree** — what was added, where.
3. **How to run** — exact commands for the demo + tests.
4. **Test results** — real output (paste it), not "tests pass."
5. **Key decisions & deviations** — where you diverged from this brief and why.
6. **Blockers / issues hit** — especially the stretch demo.
7. **Answers to §6 open questions.**
8. **Anything in the design that reality contradicted.**
9. **Proposed scope for Handoff 2** (your view — I'll decide, but I want your read).

---
*Handoff 1 · architect: Claude · design v0.2 · spine only, no cache/checkpoint/engine.*
