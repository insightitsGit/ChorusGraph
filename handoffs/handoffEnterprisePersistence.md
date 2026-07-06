# Handoff — Enterprise Persistence (Postgres, license-gated, 5th ChorusStack port)

**Director:** Amin · **Repo:** ChorusGraph (this repo) · **Companion:** `PrismRagLib/handoffs/handoff1_licensing.md`
**Why:** ChorusGraph's Enterprise tier lists "Postgres roadmap commitment (when ready)" — a vague, undated
promise. This handoff turns it into a real, license-gated capability, using the exact open-core pattern
already proven by PrismRAG (free core + one paid unlock), applied to persistence instead of retrieval.

**Strategic framing (do not deviate without checking with the Director):**
- **ChorusGraph stays fully open-source, one repo, Apache-2.0.** No separate proprietary fork.
- SQLite persistence (checkpointing + Cortex graph store) remains the **free, default, fully-functional**
  path — safe and correct for single-instance deployments. Never degrade or cripple it to push the sale.
- Postgres persistence is the **paid unlock** — sold on real multi-replica/HA correctness, not on
  artificial restriction. The free tier isn't crippled; the paid tier solves a problem the free tier
  genuinely can't (concurrent-writer safety across replicas).
- **License check lives in the open code, visible and auditable.** Gating logic is not obfuscated —
  a security-conscious buyer can read exactly what the license unlocks. That transparency is itself a
  trust asset for this audience.

---

## 0. Verified starting state (read before building)

- **Checkpointing-to-Postgres already works** — `chorusgraph/core/persistence.py::postgres_checkpointer`
  wraps the real `prismlang.AsyncPostgresCheckpointer`. **It is currently completely ungated** — anyone
  can call it today, free, in the open-source package. Part of this handoff is adding a license gate to
  something that already works, not building it from scratch.
- **Cortex/memory has no Postgres counterpart** — only `chorusgraph/persistence/sqlite_graph_store.py`
  (`SqliteGraphStore`) exists. This is real, new engineering: a `PostgresGraphStore` implementing the
  same interface (`close`, `_load`/`_save` equivalents, `node_count`, `edge_count`,
  `find_node_by_label`, `find_similar_node`, `current_edge`, `current_edges_from`, `retrieve`,
  `version`, `tombstones`, `apply`, `prune_to`, `forget_source`) against a real Postgres schema — not a
  quick connection-string swap. Scope it honestly at that size.
- **No persistence port exists in `chorusgraph/compose/ports.py`** — only `CacheBackend`, `MemoryBackend`,
  `ToolBackend`, `RetrievalBackend`. This handoff adds the 5th.
- **The license mechanism this depends on is being built in the companion handoff**
  (`PrismRagLib/handoffs/handoff1_licensing.md`, T1: offline/air-gap-capable signed license validation).
  **Do not duplicate that work here.** If it isn't done yet when you start this, either wait for it or
  coordinate to extract it into a small shared package both `prismrag_patch` and `chorusgraph` import —
  check with the Director on packaging (new tiny `prism-license` package vs. folding into
  `prismlib-plus`, which both products already depend on).

---

## T1 — Shared license validator (coordinate with the PrismRAG handoff, don't duplicate)

**Goal:** one license-validation mechanism, reused by PrismRAG's remap gate and ChorusGraph's persistence
gate. Not two parallel systems with two air-gap bugs to fix separately.

1. Confirm with the Director / check `PrismRagLib/handoffs/handoff1_licensing.md`'s status — is the
   offline-capable validator (online key OR signed offline file, zero network calls in the offline path)
   done, in progress, or not started.
2. If it's done: import it. If it's in progress: coordinate rather than fork a second implementation.
   If it doesn't exist yet: this handoff is blocked on that one — say so plainly rather than building a
   throwaway duplicate "just for ChorusGraph" that becomes two things to maintain and fix later.
3. Add a `chorusgraph.licensing` thin wrapper (or equivalent) that calls the shared validator with
   `feature="enterprise_persistence"` (or similar) so multiple gated features can share one mechanism
   with per-feature entitlement, not one all-or-nothing key.

**Exit criteria:** `chorusgraph` and `prismrag_patch` both depend on the same underlying validation code
(not copy-pasted); a license file/key that unlocks one product's feature does not automatically unlock
the other's unless the entitlement payload explicitly grants both — verify this is a deliberate,
tested choice, not an accident of shared code.

---

## T2 — `PersistenceBackend` port on `ChorusStack` (the 5th port)

**Files:** `chorusgraph/compose/ports.py`, `chorusgraph/compose/stack.py`, `chorusgraph/compose/defaults.py`

1. Add a `PersistenceBackend` Protocol (or two narrower ones — `CheckpointBackend` +
   `GraphStoreBackend` — decide based on whether they're always swapped together; likely yes for a
   real Postgres deployment, so one combined port is probably cleaner. Flag your reasoning in the return).
2. `ChorusStack.resolve_persistence()` defaults to the SQLite path (today's behavior, unchanged, free).
3. `ChorusStack.with_persistence(backend)` swap method — **use `dataclasses.replace`, not a hand-copied
   field list.** This exact bug (hand-copied constructor dropping fields silently) was already found and
   fixed twice in this codebase (`with_cache`, then again pattern-matched for `with_retrieval`) — don't
   introduce it a third time.
4. The Postgres-backed implementation of this port is gated (T3) — constructing it without a valid
   license raises a clear, actionable error naming the missing license, not a silent fallback to SQLite
   (unlike the retrieval backend's graceful degradation — persistence silently falling back would mean a
   customer *thinks* they're on durable Postgres in production and are actually silently back on SQLite,
   which is a much worse failure mode than a missing RAG feature. Fail loud here, not soft.)

**Exit criteria:** unit tests mirroring the existing `test_compose_stack.py` pattern — default resolves
to SQLite, `with_persistence(unlicensed_postgres_backend)` raises clearly, `with_persistence` uses
`dataclasses.replace` (all-fields-preserved regression test, same as the cache/retrieval ports).

---

## T3 — Gate the existing Postgres checkpointer

**Files:** `chorusgraph/core/persistence.py`

1. Wrap `postgres_checkpointer(...)` (or its call site via the new port) with the T1 license check.
   No valid entitlement → raise a clear `LicenseError`-equivalent naming what's missing and how to get
   it (link to the enterprise contact path), not a cryptic failure.
2. Confirm this doesn't break any existing internal/test usage that currently calls
   `postgres_checkpointer` directly without a license (search the codebase for call sites first).

**Exit criteria:** calling the checkpointer through the gated path without a license fails with a clear,
actionable message; calling it with a valid license (test license/mock entitlement) succeeds exactly as
it does today.

---

## T4 — Build `PostgresGraphStore` (the real new engineering)

**Files:** new `chorusgraph/persistence/postgres_graph_store.py`

1. Design the schema: nodes, edges, tombstones, version tracking — read `sqlite_graph_store.py` fully
   first; the Postgres implementation should be behaviorally equivalent, not a reinterpretation.
2. Implement every method `SqliteGraphStore` exposes (see §0's list) against Postgres, with real
   **concurrent-writer correctness** — this is the entire point of the paid tier, so it needs a real
   concurrency test (two connections writing near-simultaneously, verify no corruption/lost writes),
   not just a connection-string swap that happens to pass single-writer tests.
3. Migrations: reuse the versioned-migration pattern already established for SQLite (E5) — don't invent
   a second migration system.
4. Gate construction behind the T1 license check, same pattern as T3.

**Exit criteria:** every `SqliteGraphStore` test in the existing suite has a `PostgresGraphStore`
counterpart (skipped without a real Postgres DSN — never faked); a genuine concurrent-write test proves
the actual value proposition (multi-replica safety) works, not just that the API surface matches.

---

## T5 — Update the Enterprise tier collateral to reflect reality

**Files:** `docs/ENTERPRISE_READINESS.md`, whitepaper, landing page handoff (once this is real)

Replace "Postgres roadmap commitment (when ready)" with the actual, true statement once T1–T4 land:
what's included, what license tier it requires, and — if multi-replica k8s deployment is now genuinely
safe with this in place — update the earlier honest caveat about SQLite + k8s multi-replica risk
accordingly. Don't leave the old caveat sitting alongside a new capability that resolves it.

---

## Order

T1 (blocking — coordinate with the PrismRAG handoff) → T2 (port scaffolding) → T3 (cheap — gate what
already works) → T4 (the real engineering, biggest task) → T5 (collateral truth-up, last).

## Non-goals for this handoff

- Do not touch PrismRAG's remap licensing logic directly — that's the companion handoff's scope.
  Only the *shared validator extraction* (T1) touches both repos, and only if coordinated.
- Do not build a separate closed-source "enterprise edition" repo — explicitly out of scope per the
  strategic framing at the top.
- Do not silently degrade the free SQLite path in any way to make Postgres more attractive. If you find
  yourself tempted to make the free tier worse to sell the paid tier, stop and flag it instead.

## Return format

Per task: files · exit criteria pass/fail with real command output · the T1 coordination outcome
(shared validator used, or blocked, stated plainly) · the concurrent-write test result for T4
specifically, since that's the actual value being sold · anything left undone, stated plainly. No
commits unless the Director asks.

---
*Enterprise Persistence · one open-source repo, Postgres as the license-gated 5th port · free SQLite path
never degraded · shared license validator with PrismRAG, not duplicated · fixes the vague "Postgres
roadmap" line in the Enterprise tier with a real, testable capability.*
