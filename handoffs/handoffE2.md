# Handoff E2 — Resilience

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/ENTERPRISE_READINESS.md`](../docs/ENTERPRISE_READINESS.md) **§E2** · [`../docs/PROCESS.md`](../docs/PROCESS.md).
**Depends on:** E1 (CI + deterministic tests). **Return in:** `handoffs/handoffbackE2.md`.

## 0. Operating rules
No fakes; recorded fixtures for tests (E1). Behavior-preserving except added fault-tolerance. One bounded increment.

## 1. Goal
The runtime survives failure gracefully — **one node/tool/service failing never crashes the whole graph.**

## 2. Deliverables
- **Timeouts + retries (exponential backoff) + circuit-breakers on every external call:** Gemini, tools (Frankfurter), DB (Postgres/SQLite), Cortex.
- **Graceful degradation** — a single node/tool/LLM failure yields a clean **partial result** with a typed error recorded in the Route Ledger, not an unhandled exception.
- **Error taxonomy** — typed errors (transient vs permanent, retryable vs not); consistent handling + logging.
- **Idempotency** where retries can duplicate (digests, writes).

## 3. Out of scope
E1 (done) · E3–E9 · MVP H10 fixes · new product features.

## 4. Acceptance criteria
- [ ] Fault-injection test: kill a tool / DB / LLM mid-run → graph stays responsive, returns a clean partial result, logs a **typed** error — no crash.
- [ ] Every external call has a timeout + bounded retry + breaker; verified by test.
- [ ] Retried operations are idempotent (no duplicate side effects).
- [ ] Deterministic tests green in CI (E1); no runtime regressions.

## 5. Open questions for handoffbackE2
1. Circuit-breaker approach/lib and retry-policy defaults.
2. How partial results surface to the caller (shape/contract).
3. Where the graph was most fragile before this.
4. Proposed E3 scope.

## 6. Return format
Summary · file tree · how to run (incl. the fault-injection test) · CI result · decisions/deviations · blockers · answers to §5 · proposed E3.

---
*Handoff E2 · enterprise track · resilience · no whole-graph crash on one failure.*
