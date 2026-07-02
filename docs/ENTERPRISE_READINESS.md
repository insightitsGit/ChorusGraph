# ChorusGraph — Enterprise Readiness (post-MVP hardening plan)

**Positioning:** This is the **hardening phase that runs AFTER the MVP is complete** (H1–H9 + the
benchmark result). Clean path: finish the MVP and get the numbers first; *then* harden. **Nothing here
starts until H9 is done.** This doc drives the E-series handoffs the way `BENCHMARK.md` drove H8/H9, under
the same rules (`PROCESS.md`: no fakes, verify-against-code, honest deferral, one bounded increment).

**Prerequisite gate:** ☐ MVP complete (H1–H9) ☐ benchmark result in hand (`BENCHMARK_RESULTS.md`).

---

## Why this is a separate track
"Enterprise-grade" is defined by the **-ilities** (reliability, security, observability, scalability,
operability), not features. Those are ~half the total effort and never show in a demo. The MVP proves the
*concept*; this track makes it *sellable to a regulated buyer*. Don't conflate the two milestones.

## Current scorecard (baseline — update as phases land)

| Dimension | Status |
|---|---|
| Architecture / code structure | ✅ Solid |
| Functional test suite | ✅ Solid — but needs live keys / hits real APIs (no deterministic CI tier) |
| CI/CD + release engineering | 🔴 Gap |
| Code-quality gates (lint/type/format) | 🔴 Gap |
| Error handling / resilience | 🟡 Partial |
| Observability / ops | 🟡 Partial (Route Ledger strong; rest missing) |
| Security / compliance (§21) | 🔴 Gap — designed, not built |
| Performance / scale | 🔴 Gap — unvalidated |
| Data / persistence robustness | 🟡 Partial |
| Multi-tenant isolation | 🟡 Partial |
| API stability + reference docs | 🟡 Partial (0.x) |
| Deployment / packaging | 🔴 Gap |

---

## The hardening phases (foundation-first)

Each phase = one or more E-series handoffs. Order matters: **E1 first** — CI + a test tier that runs
without live keys is the ground everything else stands on.

### E1 — Engineering foundation
- [ ] CI pipeline (GitHub Actions): tests + lint + type-check on every PR.
- [ ] **Deterministic test tier** — record LLM/tool fixtures so the suite runs with **no live keys**; keep a small live-integration tier behind a flag.
- [ ] Coverage measured + a floor enforced.
- [ ] Lint (ruff) + format (black) + type-check (mypy) gates.
- [ ] Dependency lockfile + pinned versions; SBOM.
- [ ] Release process: semver, changelog, tagged builds.
- **Acceptance:** a green PR gate runs the full suite with no secrets; coverage reported; a tagged release is reproducible.

### E2 — Resilience
- [ ] Timeouts + retries + circuit-breakers on **every** external call (Gemini, tools, DB, Cortex).
- [ ] Graceful degradation: one node failing never crashes the whole graph.
- [ ] Error taxonomy + consistent handling; idempotency where needed.
- **Acceptance:** a fault-injection test (kill a tool/DB/LLM mid-run) leaves the graph responsive with a clean partial result, not a crash.

### E3 — Security (§21 build-out)
- [ ] Tool execution sandboxing + allowlists + capability scoping.
- [ ] mTLS/TLS default for transport; CHORUS cipher **audited or opt-in-off**.
- [ ] authn/authz for federated PrismAPI; per-request authorization.
- [ ] Cache-poisoning controls (per-tenant isolation, write-auth, provenance).
- [ ] PII redaction in ledger/logs; retention policy.
- [ ] SAST + SCA (dependency CVEs) + secrets-scanning in CI; threat model doc.
- **Acceptance:** external security review passes the ship-gate items (§21); no high/critical SCA findings; the crypto is either audited or off by default.

### E4 — Observability / ops
- [ ] Structured logging (levels, correlation IDs).
- [ ] OpenTelemetry traces + metrics export (the H1-deferred item).
- [ ] Health/readiness endpoints.
- [ ] Alerting + runbooks for the common failure modes.
- **Acceptance:** a running instance exposes traces/metrics/health to a standard stack (Grafana/Jaeger/Datadog); an on-call could diagnose a failing turn from the telemetry alone.

### E5 — Durable & scalable persistence
- [ ] Durable Cortex GraphStore (Postgres / customer datastore) — the flagged gap.
- [ ] Schema migrations (ADR-003), backup/restore.
- [ ] Data retention + right-to-forget wired product-wide (Cortex `forget()` surfaced).
- **Acceptance:** memory + state survive a full restart; a documented restore works; a delete request provably erases across all layers.

### E6 — Multi-tenant isolation
- [ ] Verified isolation across cache, ledger, memory, checkpoint (not just projection).
- [ ] Per-tenant resource limits + noisy-neighbor protection.
- **Acceptance:** a cross-tenant leakage test suite passes; one tenant cannot exhaust another's resources.

### E7 — Performance & load
- [ ] (H9 benchmark done by now — per-task cost/latency/accuracy.)
- [ ] **Load/traffic/throughput test** (director-designed) — concurrency, sustained load, memory/leak profiling.
- **Acceptance:** documented throughput + latency under sustained concurrent load; no leaks over a soak test.

### E8 — Deployment & packaging
- [ ] Product Dockerfile + deployment manifests (k8s/helm).
- [ ] 12-factor config management; dev/staging/prod separation.
- [ ] The "point it at one Postgres" install story, productized.
- **Acceptance:** a clean deploy from scratch on a fresh environment via documented steps.

### E9 — API 1.0
- [ ] Freeze the public API surface; deprecation/versioning policy.
- [ ] Reference docs (docstrings → published API docs) + tutorials.
- [ ] Resolve the packaging namespace (`chorusgraph` vs `prismlib-plus[orchestrator]`).
- **Acceptance:** a 1.0 release with a stability guarantee and complete public docs.

---

## Honest sizing
This track is **comparable in effort to the MVP feature build** — not because the code is weak, but
because enterprise-grade *is* these -ilities. Sequence it foundation-first (E1), do security (E3) before
any real customer touches it, and treat E7's load test as the gate to any scale claim.

*Post-MVP · a plan, not a promise · drive it with E-series handoffs after H9.*
