# Handoff E4 — Observability / Ops

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/ENTERPRISE_READINESS.md`](../docs/ENTERPRISE_READINESS.md) **§E4** + DESIGN **§22** · [`../docs/PROCESS.md`](../docs/PROCESS.md).
**Depends on:** E1. **Return in:** `handoffs/handoffbackE4.md`.

## 0. Operating rules
No fakes; recorded fixtures. One bounded increment. The Route Ledger already exists — extend, don't duplicate.

## 1. Goal
An operator can diagnose a failing turn **from telemetry alone** — no code reading required.

## 2. Deliverables
- **Structured logging** — levels, correlation/request IDs, JSON output.
- **OpenTelemetry** — traces + metrics export (the H1-deferred item): a span per node, enriched with cache score, grounding score, tokens, and `rule_chain` (§22).
- **Health/readiness endpoints.**
- **Alerting hooks + runbooks** for the common failure modes (LLM error, tool timeout, cache miss storm, DB down).

## 3. Out of scope
E1–E3 · E5–E9 · MVP fixes · new product features.

## 4. Acceptance criteria
- [ ] A running instance exports **traces + metrics + health** to a standard stack (Grafana / Jaeger / Datadog).
- [ ] Logs are structured with correlation IDs that tie to ledger `run_id`.
- [ ] An on-call can reconstruct a failing turn (which node, why, timing, tokens) from telemetry alone.
- [ ] OTel spans and the Route Ledger are consistent (no divergence).
- [ ] Deterministic tests green (E1).

## 5. Open questions for handoffbackE4
1. OTel exporter/backend chosen.
2. The metric set (latency, cost, cache-hit, error-rate, per-node) and the log schema.
3. How ledger `run_id` maps to the trace ID.
4. Proposed E5 scope.

## 6. Return format
Summary · file tree · how to run (show telemetry from a real turn) · decisions/deviations · blockers · answers to §5 · proposed E5.

---
*Handoff E4 · enterprise track · observability · diagnose from telemetry alone.*
