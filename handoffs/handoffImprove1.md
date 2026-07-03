# Handoff Improve-1 — Send, Subgraphs, Per-node Durability, Ergonomics, Compat (one package)

**Director:** Amin · **Architect:** Claude · **Engineer:** Cursor
**Refs:** [`docs/ENGINE_DESIGN_v0.1.md`](../docs/ENGINE_DESIGN_v0.1.md) · [`docs/CACHE_PROFILES.md`](../docs/CACHE_PROFILES.md) · [`handoffH20.md`](handoffH20.md) (T6 interrupt mechanism is extended here)
**Date issued:** 2026-07-03

---

## 0. Why one handoff

These items are one package because they all touch the same scheduler write path, and together they
attack **communication latency** — the thing our runtime is supposed to win at:

| Item | Latency lever |
|---|---|
| Per-node pending writes | a crash among N parallel nodes re-pays **1** LLM call, not N |
| Send (dynamic fan-out) | branches pass the **cache gate individually** + near-duplicate branches dedup via 64-d projection → fewer LLM calls per fan-out |
| Quorum joins | k-of-n / timeout joins → stop waiting for straggler branches |
| Subgraphs | boundary crosses as **envelope (vector + artifact ref), not full state JSON** |
| Subgraph-level CacheProfile | one hit skips an **entire sub-pipeline** (M nodes, K LLM calls at once) |
| CHORUS batch frame | N branch envelopes ship as **one tensor batch**, not N JSON round-trips (contract now, wire in P5) |

**Standing rules:** deterministic-first · all inter-node communication is PrismEnvelope on the bus (never raw dict) · no mocks/fakes (recorded fixtures OK, fabricated numbers never) · latency claims only from measured runs · commit/push only when the Director asks (trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`) · the langgraph grep gate on `chorusgraph/{core,checkpoint,compat,transport}` holds after every task.

Verify every Prism symbol you touch with a 2-line `inspect` check before coding against it; flag
deviations in the return, don't improvise.

---

## PART A — Engine (T1–T6, strict order)

### T1 — Per-node durability: pending writes
**Files:** `chorusgraph/core/persistence.py` · `chorusgraph/core/scheduler.py`

1. `prismlang.AsyncPostgresCheckpointer.aput_writes` exists (verified surface) — wire it. Add
   `EngineCheckpointer.put_writes(config, super_step, node_id, update)` (+ async), with a JSON-file
   fallback for the local backend.
2. Scheduler: as each node's update lands in `_super_step`/`_super_step_async` (BEFORE the write
   phase/barrier), persist it as a pending write keyed `(thread_id, super_step, node_id)`.
3. Resume: when `_init_run` restores mid-step, load pending writes for `(thread_id, super_step)`;
   nodes with a stored write are **skipped** (their update replayed), only missing nodes execute.
4. Clear pending writes for a step once its boundary checkpoint lands.

**Exit test:** 3 parallel nodes; node C raises on first run; re-invoke ⇒ A and B do NOT re-execute
(count via stub client), C runs, final state identical to a clean run.

### T2 — Ergonomics: `Command` + interrupt-returns-value
**Files:** `chorusgraph/core/node.py` · `chorusgraph/core/scheduler.py` · `chorusgraph/core/ir.py`

1. `Command(update: dict | NodeUpdate, goto: str | list[str] | None)` as a legal node return.
   `goto` overrides declared edges but is **validated against declared successors** (undeclared target
   ⇒ error — keep the determinism rail). Applied in `_write_and_route`; record `route_via="command"`
   on the ledger step.
2. `value = ctx.interrupt(payload)` — extend H20-T6: first execution raises the halt (checkpoint +
   pending writes per T1); on resume the SAME call **returns** the human-provided value. LangGraph's
   exact shape, so the compat shim can translate their `interrupt()` 1:1.

**Exit tests:** Command routes + updates in one return, undeclared goto raises; interrupt round-trip
returns the resume value inside the node body.

### T3 — Send: dynamic fan-out (the big one)
**Files:** `chorusgraph/core/channels.py` · `chorusgraph/core/scheduler.py` · `chorusgraph/core/ir.py` · `chorusgraph/core/node.py`

**API:** a node returns `Send(target, payload)` items (list or via `Command(goto=[Send,...])`).
Each Send becomes a **branch task** in the next super-step: same target node, **branch-local state**
(`payload` merged over a read-only snapshot view), `branch_id = f"{send_node}:{super_step}:{i}"`
(deterministic, sorted — no randomness).

**Mechanics:**
1. Branch execution: all branches of a step run concurrently (existing `asyncio.gather` path);
   per-branch updates are pending-written (T1) so one failed branch never re-pays the others.
2. **Branch envelopes:** each branch's output is a PrismEnvelope whose `rule_chain` carries the
   branch_id — provenance survives the fan-out.
3. **Cache-gate per branch:** every branch passes the node-entry interceptor with the branch payload
   as input (profile-governed per CACHE_PROFILES). This is where fan-out gets cheap: repeated branch
   inputs (same drug pair, same doc chunk) skip their LLM call.
4. **Fan-out dedup:** before spawning, project each branch payload to 64-d (`project_text` /
   `project_from_raw`) and merge branches whose vectors are exact-duplicate at the coarse threshold
   from `measured_thresholds()` — merged branches share one execution, results fan back to all
   requesters. Dedup decisions logged on the ledger (`branches_requested` vs `branches_executed`) —
   **no silent merging**.
5. **Join:** the reduce node declares `join="all" | ("quorum", k) | ("timeout", ms)`. Scheduler
   activates the join node when the policy is satisfied; late branch results still write their
   channels (reducers are order-deterministic), but the join doesn't wait. Timeout uses the injected
   clock (no bare `datetime.now` in engine logic — resume safety).
6. Recursion/width limits: `max_branches` config (default 64); exceeding raises, never truncates
   silently.

**Exit tests:** map-reduce over a runtime-decided list (N unknown at compile time) · dedup: 5 branches
with 2 duplicates ⇒ 3 executions, 5 results · quorum 2-of-3 activates join early, straggler's write
still lands · branch crash + resume re-runs only that branch (T1 integration) · deterministic branch
ordering across two identical runs.

### T4 — Subgraphs (local)
**Files:** new `chorusgraph/core/subgraph.py` · `chorusgraph/core/graph.py` (`add_subgraph`) · `chorusgraph/core/persistence.py` · `chorusgraph/core/trace.py`

1. `g.add_subgraph(name, compiled_child, *, input_map, output_map)` — a node whose handler invokes a
   child `CompiledGraph`. Maps are explicit dicts (parent channel → child channel and back); no
   implicit shared-name leakage (tighter than LangGraph, deliberate).
2. **Boundary = envelope:** the child receives the parent's envelope (vector + compact artifact),
   not the full parent state. If parent/child taxonomies differ, re-project at the boundary via
   `prismlang.BoundaryTranslator.translate` (verify signature first).
3. **Namespaced checkpoints:** child thread_id = `f"{parent_thread}:{node_name}"` on the SAME
   checkpointer — resume works at any depth; an interrupt inside the child surfaces to the parent's
   caller with the namespaced path.
4. **Nested ledger:** child `LedgerStep`s carry `parent_run_id` + the subgraph node name; `get_run`
   can reconstruct the tree.
5. **Subgraph-level CacheProfile:** the subgraph node takes a profile like any node — a fingerprint
   hit on the subgraph's input skips the ENTIRE child run and replays its cached output envelope
   (quality-gated seeding rules from H21 apply to what gets seeded).

**Exit tests:** parent↔child mapping round-trip · interrupt inside child, resume from parent ·
nested ledger tree · subgraph cache hit ⇒ 0 child LLM calls (stub client count).

### T5 — Remote subgraph contract (location: chorus | prismapi)
**Files:** `chorusgraph/core/subgraph.py` · `chorusgraph/transport/*`

`add_subgraph(..., location="local"|"chorus"|"prismapi")`. Non-local locations route the boundary
envelope through the existing `TransportRouter` spines. **Honesty constraint:** the spines are still
contract stubs (P5/P6 of `handoffCORE_MVP.md`) — implement and test the contract (encode → route →
decode round-trip in-memory, namespace + ledger correctness), and mark real network wiring as P5/P6
debt in the return. Do NOT fake a network latency number.

### T6 — CHORUS batch frame for fan-out
**Files:** `chorusgraph/transport/chorus.py` · `chorusgraph/core/scheduler.py`

`ChorusBatchFrame`: N branch envelopes of one Send = one frame (vectors are fixed-size float32 —
a natural tensor batch: `shape (N, 64)` + artifact refs). Scheduler hands the whole branch set to the
transport when the target is non-local. Contract + encode/decode + property test now; wire-level
measurement lands with P5.

---

## PART B — Edges (T7–T8, start after T3 is green; parallelizable)

### T7 — Functional API
**Files:** new `chorusgraph/func.py`

`@entrypoint(checkpointer=...)` + `@task` decorators building a `Graph` under the hood; awaiting a
task = an edge; `Send`-style fan-out via list comprehension over task calls. Pure sugar — zero engine
changes; every feature must compile down to the same IR (assert in tests).

### T8 — Compat adapters (each its own small PR-shaped unit)
**Files:** `chorusgraph/compat/*` · `tests/compat/*`

1. **Conformance suite:** a corpus of ≥10 real LangGraph graph definitions (from their docs patterns:
   ReAct, supervisor, map-reduce w/ Send, subgraph, interrupt) run through `compile_state_graph` in CI.
   Failures are listed, not skipped.
2. **Checkpoint import:** CLI that reads LangGraph SQLite/Postgres checkpoints → ChorusGraph threads
   (namespaced per T4 rules). Real fixture DB in tests.
3. **Tool duck-typing:** `ToolNode` accepts anything with `.invoke`/`.name` (LangChain tools) —
   optional extra, `langchain` never imported by core. Also: consume MCP tools via `prism.api.mcp`
   (verify that surface first; if it's not usable, say so in the return).
4. **Ledger → OpenTelemetry exporter:** spans per LedgerStep with `rule_chain`/cache attrs.

---

## Order, gates, schedule

T1 → T2 → T3 → T4 → T5 → T6, then T7 ∥ T8. Full `python -m pytest tests/ -q` green after each task;
grep gate always. Rough effort: T1 2d · T2 1d · T3 4–5d · T4 3d · T5 2d · T6 1–2d · T7 2d · T8 3–4d.

**Benchmark note:** after T3+T4, add ONE offline measured scenario (stub client, recorded fixtures):
healthcare depth-6 with fan-out over drug pairs + subgraph cache — report `branches_requested /
branches_executed / llm_calls / wall_ms` vs the pre-Improve1 engine on the same fixture. Measured or
absent — no projections.

## Return format (`handoffbackImprove1.md`)

Per task: files · exit-criteria pass/fail with real command output · Prism signature deviations ·
what was contract-only vs actually wired (T5/T6 especially) · the offline measured numbers · anything
blocked, stated plainly. No commits unless the Director asks.

---
*Improve-1 · Send + subgraphs + pending writes + Command/interrupt + functional API + compat adapters ·
one package because they share the scheduler write path and together they are the latency story.*
