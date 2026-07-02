# Handoff E5 — Durable & Scalable Persistence

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/ENTERPRISE_READINESS.md`](../docs/ENTERPRISE_READINESS.md) **§E5** + DESIGN **§13.4** · [`../docs/PROCESS.md`](../docs/PROCESS.md).
**Depends on:** E1. **Return in:** `handoffs/handoffbackE5.md`.

## 0. Operating rules
No fakes; recorded fixtures. One bounded increment. Real Postgres for the durable tests.

## 1. Goal
Memory + state survive restarts; the data lifecycle (migrate, backup, delete) is real.

## 2. Deliverables
- **Durable Cortex GraphStore** — Postgres-backed L3 (closes the flagged `InMemoryGraphStore` gap): the knowledge graph survives a process restart, not just the answer cache.
- **Schema migrations** — versioned (ADR-003) for ledger + checkpoint + cortex stores.
- **Backup/restore** — documented + a tested restore.
- **Retention + right-to-forget** — Cortex `forget()` surfaced product-wide; a delete provably erases across cache, ledger, memory, checkpoint.

## 3. Out of scope
E1–E4 · E6–E9 · MVP fixes · multi-DB connectors beyond Postgres (Phase 2, note only).

## 4. Acceptance criteria
- [ ] Cortex memory + graph state **survive a full restart** (verified).
- [ ] Migrations run forward cleanly on an existing DB; versioned.
- [ ] A documented backup → restore round-trip works.
- [ ] A delete request **provably erases** the subject's data across every layer (test proves no residue in cache/ledger/memory/checkpoint).

## 5. Open questions for handoffbackE5
1. Postgres schema for the bitemporal Cortex graph (nodes/edges/validity).
2. Migration tool chosen.
3. Where deletion was hardest to guarantee across layers.
4. Multi-DB (beyond Postgres) — defer to Phase 2? Your read.
5. Proposed E6 scope.

## 6. Return format
Summary · file tree · how to run (restart-survival + delete tests) · decisions/deviations · blockers · answers to §5 · proposed E6.

---
*Handoff E5 · enterprise track · durable memory + data lifecycle.*
