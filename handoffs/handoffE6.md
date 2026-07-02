# Handoff E6 — Multi-Tenant Isolation

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/ENTERPRISE_READINESS.md`](../docs/ENTERPRISE_READINESS.md) **§E6** · [`../docs/PROCESS.md`](../docs/PROCESS.md).
**Depends on:** E1, E5. **Return in:** `handoffs/handoffbackE6.md`.

## 0. Operating rules
No fakes; recorded fixtures. One bounded increment. Isolation is verified by tests, not asserted.

## 1. Goal
**Airtight** tenant isolation across every layer + resource fairness between tenants.

## 2. Deliverables
- **Verified isolation** across cache, ledger, memory (Cortex), and checkpoint — not just the per-tenant projection. `tenant_id` enforced server-side everywhere; no cross-tenant read path.
- **Per-tenant resource limits** — rate/quota/memory caps; noisy-neighbor protection.
- **A cross-tenant leakage test suite** — attempts to reach tenant A's data as tenant B in each layer, all denied.

## 3. Out of scope
E1–E5 · E7–E9 · MVP fixes.

## 4. Acceptance criteria
- [ ] Cross-tenant leakage test suite **passes** — no data from tenant A reachable by tenant B in cache, ledger, memory, or checkpoint.
- [ ] Per-tenant limits enforced; one tenant cannot exhaust another's resources (verified).
- [ ] Isolation holds under the durable stores from E5.

## 5. Open questions for handoffbackE6
1. Which layer was weakest on isolation before this.
2. Resource-limit mechanism (rate limiter / quota / pool caps).
3. Any shared global state that had to be tenant-scoped.
4. Proposed E7 scope.

## 6. Return format
Summary · file tree · how to run (the leakage + limit tests) · decisions/deviations · blockers · answers to §5 · proposed E7.

---
*Handoff E6 · enterprise track · airtight tenant isolation + fairness.*
