# Handoff H20 — Engine gap fixes (design ↔ code review findings)

**Director:** Amin · **Architect:** Claude · **Engineer:** Cursor
**Spec refs:** [`docs/ENGINE_DESIGN_v0.1.md`](../docs/ENGINE_DESIGN_v0.1.md) · [`docs/DESIGN_v0.3_PRISM_ENGINE.md`](../docs/DESIGN_v0.3_PRISM_ENGINE.md) · [`handoffCORE_MVP.md`](handoffCORE_MVP.md)
**Date issued:** 2026-07-02

---

## 0. Context — where we are

The Architect ran a full design-vs-code review of the new engine (`chorusgraph/core/`). Verdict:
**P1–P4 are substantially delivered and real** — BSP scheduler, envelope channels + reducers, native
DSL, Resonance bus wiring, prismlang persistence, static interrupts, cache interceptor, native Route
Ledger, role multi-agent example, `compat.langgraph` shim. Test suite: **176 passed / 1 failed / 2
skipped**. CI gate holds: **zero `langgraph` imports in `chorusgraph/core`**.

This handoff closes the **8 gaps** the review found. Work them **in the order given** (T1 → T6);
T7/T8 are explicitly deferred — do NOT start them in this handoff.

**Standing rules (unchanged, non-negotiable):** deterministic-first (no gratuitous LLM calls) ·
all inter-node communication is Prism-native (envelope on the Resonance bus — never raw dict handoff) ·
no mocks/fakes (recorded fixtures OK; fabricated results never) · fairness in benchmarks is sacred ·
commit/push **only when the Director asks** · every task states which debt it deletes.

---

## T1 — Fix the failing cache-skip proof test  *(gap 7 — do this first)*

**File:** [`tests/test_multiagent_pipeline.py:145`](../tests/test_multiagent_pipeline.py)
**Problem:** `test_container_d_cache_hit_skips_llm_hops` calls
`seed_healthcare_cache(runtime, cache_query_key(case), payload)` **without** the now-required
`pipeline_depth` kwarg → `ValueError` in `benchmark/hc2/cache_helpers.py:57`. The production caller
(`benchmark/hc2/nodes.py:292`) passes `pipeline_depth=case.pipeline_depth` correctly — only the test
is stale.

**Fix:** pass `pipeline_depth=case.pipeline_depth` (the test case uses depth 6) at the test call site.
Do **not** add a default to `seed_healthcare_cache` — the required arg is a deliberate correctness
guard (depth-partitioned payloads must not silently cross depths).

**Exit:** `python -m pytest tests/test_multiagent_pipeline.py -q` → all pass. This is *the* test that
proves a cache hit skips the LLM hops (llm_calls == 0 on repeat) — it must be green before anything else.

---

## T2 — Make Resonance actually route  *(gap 2 — the Director's mandate, currently cosmetic)*

**Files:** [`chorusgraph/core/ir.py`](../chorusgraph/core/ir.py) ·
[`chorusgraph/core/bus.py`](../chorusgraph/core/bus.py) ·
[`chorusgraph/core/scheduler.py`](../chorusgraph/core/scheduler.py)

**Problem:** `GraphIR.successors(node, view, update, bus)` accepts `bus` and **never uses it** —
routing today is `category_slug → paths` mapping with a router-fn fallback. `bus.subscribers_for_slug()`
exists but no caller. The bus therefore only carries telemetry (frequencies on the ledger). The design
(§2.2) and the Director's explicit mandate say: **conditional edges are Resonance matches — the next
node is whoever's frequency the emitted envelope excites.**

**Fix (keep it deterministic and backward-compatible):**
1. In `GraphIR.successors`, when the node has a conditional edge AND the update carries a primary
   envelope AND `bus` is provided: resolve candidates via
   `bus.subscribers_for_slug(envelope.category_slug)`, **intersect with the edge's declared `paths`
   targets** (the paths mapping remains the safety rail — Resonance picks *among* declared successors,
   never routes to an undeclared node).
2. Resolution order: (a) Resonance subscriber match within declared paths → (b) exact slug-key match in
   `paths` (current behavior) → (c) router-fn fallback. Deterministic tie-break: sorted(node_id) first.
3. Record on the `LedgerStep` **which mechanism routed** (`route_via: "resonance" | "slug" | "router"`)
   so routing is auditable — extend `RouteTracker.record_step` and `LedgerStep` if needed.
4. `bus.register_node` must be called for every node at `compile()` with its declared `category_slug`
   (verify this happens; wire it if the DSL doesn't already).

**Do NOT** make routing depend on wall-clock, randomness, or broadcast timing — same input ⇒ same route.

**Exit:** a unit test where two declared successors subscribe to different slugs, and the emitted
envelope's `category_slug` selects the successor **via the bus** (assert `route_via == "resonance"` on
the ledger step); plus all existing routing tests still pass.

---

## T3 — Postgres persistence + real time-travel  *(gap 3 — P2's mandate, unfinished)*

**Files:** [`chorusgraph/core/persistence.py`](../chorusgraph/core/persistence.py) ·
[`chorusgraph/checkpoint/prism.py`](../chorusgraph/checkpoint/prism.py)

**Problems:**
- Only JsonFile factories exist (`json_file_checkpointer`, `async_json_file_checkpointer`).
  `prismlang.AsyncPostgresCheckpointer` — the P2 mandate, with `aput_writes`,
  `aget_delta_channel_history`, `aprune`, `acopy_thread` — is unused.
- `sqlite_checkpointer()` in `checkpoint/prism.py` now silently returns a **JSON-file** backend while
  keeping the sqlite name and ignoring `conn` — misleading API.

**Fix:**
1. Add `postgres_checkpointer(conn_string) -> EngineCheckpointer` wrapping
   `prismlang.AsyncPostgresCheckpointer`. Verify the real signature with `inspect` first (per standing
   rule); flag deviations in the return instead of working around them.
2. Wire time-travel properly: `CompiledGraph.get_state_history` should use
   `aget_delta_channel_history` when the backend provides it (fall back to `list` otherwise), and
   `update_state` should create a **forked checkpoint** (parent_config chain) rather than overwrite.
3. Rename `sqlite_checkpointer` → deprecate: keep the name as a thin alias that emits a
   `DeprecationWarning("file-backed; use json_file_checkpointer or postgres_checkpointer")` so existing
   callers don't break, and update callers in the repo to the honest names.
4. Postgres tests: mark `@pytest.mark.skipif` on missing `CHORUSGRAPH_PG_DSN` env var — real DB when
   available, **skipped not faked** when not.

**Exit:** resume + history + fork tests pass on the JsonFile backend; Postgres path exercised when DSN
present; no API that claims a backend it doesn't use.

---

## T4 — Live streaming, not batch-replay  *(gap 5 — real LangGraph parity gap)*

**File:** [`chorusgraph/core/scheduler.py`](../chorusgraph/core/scheduler.py) (`stream`, `astream`,
`_run`, `_run_async`)

**Problem:** `stream()`/`astream()` run the graph **to completion**, then yield the collected events
list (scheduler.py:165–194). Nothing is emitted while the graph runs — that is replay, not streaming.

**Fix:**
1. Refactor the run loop into a generator core: `_run_iter(...)` yields events **as each super-step's
   WRITE phase completes** (and per-node for `updates`/`messages` modes). `invoke()` = drain the
   generator and return final values; `stream()` = yield from it directly.
2. Async variant: `_arun_iter` as an async generator; `astream` yields from it; per-node events emit as
   each `run_one` completes (use `asyncio.as_completed` within the super-step for node-level updates —
   the WRITE barrier still applies before routing).
3. Token-level `messages` mode: give `NodeContext` an `emit(token_or_chunk)` hook that pushes into the
   live event stream, so an LLM node can stream tokens mid-execution. Wire the finance example's Gemini
   node to use it where the client supports streaming (real client only — no fake token chunks).
4. `GraphInterrupt` must propagate through the generator — the consumer sees events up to the halt,
   then the interrupt surfaces exactly as `invoke` does today.

**Exit:** a test that consumes `stream()` and asserts an event is received **before** a later node
executes (e.g., a 2-node graph where node B records the time it started vs when node A's event was
yielded); all 4 modes covered; interrupt-mid-stream test.

---

## T5 — Kill the legacy parallel engine  *(gap 1 — consolidation; this handoff IS the kill date)*

**Files:** [`chorusgraph/graph/builder.py`](../chorusgraph/graph/builder.py) ·
[`chorusgraph/graph/ir.py`](../chorusgraph/graph/ir.py) ·
[`chorusgraph/runtime/compiled.py`](../chorusgraph/runtime/compiled.py) ·
[`chorusgraph/runtime/state.py`](../chorusgraph/runtime/state.py) ·
[`chorusgraph/engine/context.py`](../chorusgraph/engine/context.py) ·
[`chorusgraph/__init__.py`](../chorusgraph/__init__.py)

**Problem:** two engines coexist — the ADR-004 "phase 1" native runtime (dict-state `merge_state`,
`LegacyGraph`) and the envelope-channel `core/` engine. Two schedulers, two IRs, two `Graph` classes,
both exported. Transition debt that must not calcify.

**Fix:**
1. Inventory every caller of `LegacyGraph`, `chorusgraph.runtime.compiled`, `merge_state`, and
   `PrismEngineContext` (repo-wide grep incl. benchmark + tests). Migrate each to the `core/` engine.
2. Where the legacy runtime has behavior `core/` lacks, **port the behavior into `core/`** (list each
   ported behavior in the return) — do not keep the legacy engine alive for one feature.
3. Delete `chorusgraph/graph/`, `chorusgraph/runtime/`, `chorusgraph/engine/` once callers are migrated.
   Remove `LegacyGraph`, `merge_state`, `PrismEngineContext` from `chorusgraph/__init__.py` exports.
   Update `docs/ADR-004-native-runtime.md` with a superseded-by note pointing at `core/`.
4. If a migration is genuinely blocked (e.g., a benchmark baseline needs it), **stop and flag it in the
   return** with the exact blocker — do not silently keep both engines.

**Exit:** one engine, one `Graph`, one IR; full test suite green; `git grep -l "LegacyGraph\|merge_state\|PrismEngineContext"` returns only docs/changelog mentions.

---

## T6 — Dynamic `interrupt()`  *(gap 4 — HITL parity)*

**Files:** [`chorusgraph/core/node.py`](../chorusgraph/core/node.py) ·
[`chorusgraph/core/scheduler.py`](../chorusgraph/core/scheduler.py) ·
[`chorusgraph/core/persistence.py`](../chorusgraph/core/persistence.py)

**Problem:** only static `interrupt_before`/`interrupt_after` node sets exist. LangGraph parity (and
real HITL) needs a node to call `interrupt(payload)` **mid-execution** based on what it sees.

**Fix:**
1. Add `NodeContext.interrupt(payload)` → raises an internal `NodeInterrupt(payload)`.
2. Scheduler catches it during the node phase: completes the other concurrently-running nodes of the
   same super-step, applies their updates (WRITE phase), checkpoints **with the interrupting node still
   in `active`** plus the interrupt payload in metadata, then raises `GraphInterrupt` carrying the payload.
3. Resume semantics: `invoke(resume_value, thread_id=...)` — on resume, the interrupted node re-executes
   and `ctx.resume_value` exposes the human's answer (persisted via `aput_writes`/pending-writes so a
   crash between interrupt and resume loses nothing).
4. Surface the payload on the returned state (`__interrupt__` entry) the same way static interrupts do.

**Exit:** test — node calls `ctx.interrupt({"question": ...})`; run halts; `update_state`/resume with an
answer; node completes using `ctx.resume_value`; ledger records the interrupt step.

---

## Explicitly DEFERRED — do not touch in H20

- **Gap 6 (transports are stubs):** `ChorusSpine` / `PrismAPISpine` stay contract-stubs until **P5/P6**
  of `handoffCORE_MVP.md` (wire `prism.cluster.transport` and `prism.api` from `prismlib-plus` then).
  Reason: sequencing — single-runtime engine must be consolidated (T5) and live-streaming (T4) first.
- **Gap 8 (examples migration + engine re-benchmark):** `finance_agent/graph.py`, `patterns_graph.py`,
  and the fl/fc/hl/hc re-benchmark belong to **P7**. No replacement claims until those numbers exist.

---

## Order, gates, and the one CI rule

Work strictly **T1 → T2 → T3 → T4 → T5 → T6**. Run the **full** suite after each task — a task is done
only when `python -m pytest tests/ -q` is green (plus its own new tests).

The gate that must hold after every task:
```
grep -rn "langgraph" chorusgraph/core chorusgraph/checkpoint chorusgraph/compat chorusgraph/transport → 0 code matches
```
(the docstring self-reference in `compat/langgraph.py` is allowed; after T5, add the deleted
`graph/ runtime/ engine/` dirs to the gate trivially by their absence).

---

## Return format (`handoffbackH20.md`)

Per task: **(1)** files changed, **(2)** exit-criteria pass/fail with the actual command output
(pytest tail + the grep gate), **(3)** any Prism symbol whose real signature differed from this handoff
(esp. `AsyncPostgresCheckpointer`), **(4)** behaviors ported from the legacy engine in T5 (list), and
**(5)** anything blocked or unverifiable — stated plainly, not papered over. No commits unless the
Director asks; if asked, trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---
*H20 · closes review gaps 7, 2, 3, 5, 1, 4 · defers 6 (P5/P6) and 8 (P7) by design, not omission.*
