# Handoff Improve-2 — Distribution + Federation land now (P5/P6 absorbed), compat Send gap, isolation proof, composite fixes

**Director:** Amin · **Architect:** Claude · **Engineer:** Cursor
**Refs:** [`handoffCORE_MVP.md`](handoffCORE_MVP.md) (P5/P6 are ABSORBED here — nothing stays parked) ·
[`handoffbackImprove1.md`](handoffbackImprove1.md) · [`docs/ENGINE_DESIGN_v0.1.md`](../docs/ENGINE_DESIGN_v0.1.md) §2 ·
[`docs/CACHE_PROFILES.md`](../docs/CACHE_PROFILES.md)
**Date issued:** 2026-07-03

---

## 0. Scope (Director decision)

Nothing waits in "P5/P6" anymore. This handoff contains: **(A)** two quick composite-layer fixes,
**(B)** two engine proof gaps found in the Send verification, **(C)** the full distribution +
federation work — real wiring of `RedisBroadcast`, CHORUS mesh, and PrismAPI, including
Send-over-transport — with an honest measured proof at the end. After Improve-2, the only remaining
roadmap item from CORE_MVP is P7 (example migration + matrix re-benchmark).

**Standing rules:** deterministic-first · every inter-node message is a PrismEnvelope (never raw dict)
· no mocks/fakes — recorded fixtures OK, fabricated numbers never · latency/bandwidth claims only from
measured runs, environment disclosed · verify every `prism.*` symbol with `inspect` before coding
against it and flag deviations in the return · full `python -m pytest tests/ -q` green after every
task · langgraph grep gate on `chorusgraph/{core,checkpoint,compat,transport}` after every task ·
commit/push only when the Director asks (trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`).

---

## PART A — Composite-layer fixes (quick, do first)

### T1 — ChorusStack: no hardcoded thresholds
**File:** `chorusgraph/compose/stack.py`

`coarse_threshold: float = 0.88` / `verify_threshold: float = 0.95` duplicate measured values as
literals — if thresholds are re-measured, the stack silently keeps stale numbers (the H4 leaked-demo-
thresholds lesson recurring in a new place). Fix: default both fields to `None`; resolve at
`to_cache_runtime()` time from `measured_thresholds()` / the profile registry (per-slug verify via
`verify_for(...)` where the interceptor knows the slug). Explicit constructor values still win
(escape hatch for tests). **Exit:** unit test — a stack built with no thresholds picks up a
monkeypatched `measured_thresholds()` change; explicit values override.

### T2 — ChorusStack.with_cache via `dataclasses.replace`
**File:** `chorusgraph/compose/stack.py`

Hand-copied field list drops configuration silently when a new field is added. Replace the body with
`dataclasses.replace(self, cache=backend, _cache_runtime=None)` (note: reset the cached runtime so the
swap actually takes effect — check whether the current hand-copy has this bug already and say so in
the return). **Exit:** test — add-a-field regression guard: `with_cache` result equals original on ALL
fields except `cache` (compare `dataclasses.fields` programmatically, not a hand list).

---

## PART B — Engine proof gaps (from the Send feature verification)

### T3 — Explicit branch same-key isolation test
**File:** `tests/test_send.py`

Current tests prove merge correctness implicitly; add the explicit corruption test: N parallel
branches each write the SAME scalar key and the same append-reducer key. Assert: (a) append channel
contains all N contributions after join, (b) scalar-key outcome follows the documented reducer rule
deterministically across two identical runs (same winner both times), (c) no branch sees a sibling's
write mid-step (read-back inside the branch equals its own overlay). If (b)'s rule is currently
undefined in `channels.py`, DEFINE it (deterministic, documented — e.g. last-by-sorted-branch-id) and
test it; don't leave scalar collisions to dict ordering luck.

### T4 — Compat shim: Send-from-conditional-edge translation
**Files:** `chorusgraph/compat/langgraph.py` · `tests/compat/test_conformance.py`

LangGraph spawns map branches from the conditional-edge function returning `Send` objects; we spawn
from node returns. The shim must translate: when a mirrored branch function returns `Send` objects
(or a list), synthesize a splitter node that calls the edge function and returns our `Send` list, and
rewire the edge through it. **Exit:** a real LangGraph map-reduce graph (edge-fn returning
`langgraph`-style Sends) added to the conformance PATTERNS, compiles and runs on our engine with
correct fan-out count and reduced output.

---

## PART C — Distribution + Federation (absorbing CORE_MVP P5/P6, for real)

> Order: T5 → T6 → T7 → T8. The spines stop being stubs in this handoff. First step of each task:
> `inspect` the real `prism.*` surface you're about to wire (`prismresonance.RedisBroadcast`,
> `prism.cluster.transport`, `prism.api`, `prism.bridge.vector` — from `prismlib-plus` at
> `C:\code\PrismLabPlusAPI`, editable-installed) and record the actual signatures in the return.

### T5 — Distributed bus: `RedisBroadcast` wiring (was P5a)
**Files:** `chorusgraph/core/bus.py` · new `tests/test_bus_redis.py`

`ResonanceBus(backend="redis")` exists but is untested against a real Redis. Wire + test:
registration, frequency set/get, broadcast visibility across TWO separate processes
(`multiprocessing`, not threads — this is the honest tier of "distributed"). Redis via
`CHORUSGRAPH_REDIS_URL` env; tests **skip (never fake)** when absent. Routing determinism must hold:
same envelopes ⇒ same `route_via`/successors regardless of backend. **Exit:** two-process test green
with a real Redis; single-process suite unaffected without one.

### T6 — CHORUS mesh transport: real wiring (was P5b)
**Files:** `chorusgraph/transport/chorus.py` · `chorusgraph/core/transport_router.py` · new `tests/test_transport_chorus.py`

Replace ChorusSpine's in-memory stub path with the real client from `prism.cluster.transport`
(+ `node`/`health` as needed). `ChorusBatchFrame` (the `(N, 64)` float32 batch from Improve-1 T6)
becomes the actual wire unit. Two-process loopback test: envelopes + batch frames cross a real socket,
decode identically (property test on real wire bytes, not in-memory round-trip). If
`prism.cluster.transport`'s surface can't carry the batch frame as designed, STOP and flag — do not
silently fall back to per-envelope sends.

### T7 — PrismAPI federation: real wiring + Send-over-transport (was P6 + the extension)
**Files:** `chorusgraph/transport/prismapi.py` · `chorusgraph/core/subgraph_transport.py` · `chorusgraph/core/scheduler.py` · new `tests/test_federation.py`

1. Wire `PrismAPISpine` to the real `prism.api` provider/consumer (auth per its schema);
   `prism.bridge.vector` / `BoundaryTranslator` re-projects at the boundary.
2. **Zero re-embed assertion:** instrument the embedder — a cross-boundary hop must record 0 embed
   calls on the remote side (the PrismAPI promise, tested not narrated).
3. **Send-over-transport:** `Send` branches whose target is a remote subgraph
   (`add_subgraph(..., location="chorus"|"prismapi")`) route their batch through `TransportRouter` as
   ONE ChorusBatchFrame; results fan back and join locally (all/quorum/timeout unchanged). Branch
   pending-writes must still hold across the remote leg (remote branch crash ⇒ only that branch re-runs).
4. Remote-side execution: a second process hosts the child graph as a PrismAPI provider (loopback).

**Exit:** two-process federation test — parent Sends 10 branches to a remote child, one batch frame
out, quorum-8 join, 0 remote embed calls, ledger shows `route_via`/transport per branch.

### T8 — Measured distributed proof (no fabrication, environment disclosed)
**Files:** new `benchmark/distributed_proof.py` + results dir

Same graph, same fixture (stub LLM so only TRANSPORT varies — fairness rule applied to ourselves),
three configurations: (1) single-process inproc, (2) two-process CHORUS loopback, (3) two-process
PrismAPI loopback. Report per config: `wall_ms` (real numbers, not "≥0"), bytes on the wire per hop,
round-trips for a 10-branch Send (must be 1 batch frame, not 10), embed calls on the remote side
(must be 0 for PrismAPI). Loopback is the honest tier — label it LOOPBACK, no transatlantic claims
from localhost. Azure two-VM run is a stretch goal, not a requirement; if run, disclose specs.

---

## Docs (part of T8's exit)

- `handoffCORE_MVP.md`: mark P5/P6 "absorbed into Improve-2" with a pointer here.
- `docs/ENGINE_DESIGN_v0.1.md` §2.4 table: update transport rows from "contract stub" to wired status.
- `docs/DESIGN_v0.3_PRISM_ENGINE.md` §3: same status update.

## Order & effort

T1+T2 (½ d) → T3 (½ d) → T4 (1–2 d) → T5 (1–2 d) → T6 (2–3 d) → T7 (3–4 d) → T8 (1–2 d).

## Return format (`handoffbackImprove2.md`)

Per task: files · exit pass/fail with real command output · **actual `prism.*` signatures found vs
assumed** (T5–T7 especially) · the T8 numbers table with environment disclosed · whether the
`with_cache` cached-runtime bug existed (T2) · anything blocked, stated plainly — a stopped-and-flagged
T6 is a good return; a silent fallback is not. No commits unless the Director asks.

---
*Improve-2 · P5/P6 absorbed — spines get real, Send goes over the wire, federation proves zero re-embed ·
plus compat Send-edge translation, branch isolation proof, and the two ChorusStack hygiene fixes.*
