# ChorusGraph — Enterprise Readiness

**Positioning:** Post-MVP hardening track (E1–E9) on **`master` @ v1.0.0**. MVP benchmark gate cleared
2026-07-04; enterprise track merged 2026-07-05.

---

## Current scorecard (post E-track)

| Dimension | Status |
|---|---|
| Architecture / native engine | ✅ Solid — LangGraph confined to baselines |
| Benchmark proof | ✅ Full 8-scenario matrix verified (`20260704_212111`) |
| Functional test suite | ✅ **323 passing** — deterministic CI tier (no live keys) |
| CI/CD + release engineering | ✅ GitHub Actions: pytest, ruff, mypy, coverage, SBOM |
| Code-quality gates | 🟡 **Partial** — ruff/mypy on tests + package; full `chorusgraph/` ruff deferred |
| Error handling / resilience | ✅ Breakers, retries, partial failures, fault-injection tests |
| Observability / ops | ✅ Structured logs, OTel, health/metrics, runbooks |
| Security / compliance (§21) | 🟡 **Built, not externally audited** — SAST/SCA in CI; threat model doc |
| Performance / scale | 🟡 Load harness + docs; **production SLO soak not run** |
| Data / persistence | 🟡 **SQLite durable graph** ships; Postgres Cortex = Phase 2 |
| Multi-tenant isolation | ✅ Guards + leakage tests + quotas |
| API stability + reference docs | ✅ **1.0.0 frozen** — `public.py`, `API_1_0.md`, `STABILITY.md` |
| Deployment / packaging | ✅ Dockerfile, Compose, k8s, `DEPLOY.md` |
| Retrieval plug-in | ✅ `RetrievalBackend` — keyword default, PrismRAG swap |

---

## Release readiness (1.0.0)

| Gate | Status |
|------|--------|
| `pytest` green (no secrets) | ✅ |
| CI ruff + format (tests scope) | ✅ |
| Coverage floor (71%) | ✅ |
| Lockfile + SBOM | ✅ |
| `git tag v1.0.0` | ⏸ Tag when Director approves push |
| External security review | ⏸ Phase 2 / pre-regulated-customer |
| Production load/soak SLOs | ⏸ Run `python -m benchmark.load` at target concurrency |

**Verdict:** Ready for **controlled enterprise pilot** (single-tenant, Docker/k8s, documented caveats).
**Not yet** ready for regulated multi-tenant SaaS at scale without Phase 2 items below.

---

## Hardening phases — completion

### E1 — Engineering foundation ✅
- CI pipeline, deterministic test tier, coverage floor, lockfile, SBOM, release docs

### E2 — Resilience ✅
- Timeouts/retries/breakers, graceful node failure, idempotency, fault-injection tests

### E3 — Security ✅ (build-out; external review pending)
- Tool sandbox, TLS default, federation auth, cache isolation, PII redaction, threat model, CI security job

### E4 — Observability ✅
- JSON logs, OTel traces, health/readiness, runbooks

### E5 — Durable persistence ✅ (SQLite; Postgres Phase 2)
- SqliteGraphStore, migrations, backup/restore, right-to-forget

### E6 — Multi-tenant isolation ✅
- Cross-tenant leakage tests, resource limits

### E7 — Performance & load 🟡
- Harness shipped (`python -m benchmark.load`); production SLO validation deferred

### E8 — Deployment & packaging ✅
- Dockerfile, docker-compose, k8s, deploy docs

### E9 — API 1.0 ✅
- Frozen public surface, stability guarantee, v1.0.0

### PrismRagPlugin ✅
- `RetrievalBackend` port; HC1/HC2 on library surface

---

## Phase 2 backlog (pre scale / regulated production)

1. **Postgres-native Cortex GraphStore** — replace SQLite for multi-instance durability
2. **CHORUS cipher audit** — currently opt-in only; TLS is default
3. **Full-package ruff** — ~2300 legacy findings in `chorusgraph/`
4. **Production load/soak** — Azure or staging SLO run with Director targets
5. **External penetration test** — third-party sign-off for regulated buyers
6. **`prismlib-plus[orchestrator]` namespace** — deferred; `chorusgraph` retained for 1.x

---

## How to verify locally

```powershell
# CI-equivalent (deterministic tier)
ruff check tests .github
ruff format --check tests .github
mypy chorusgraph --config-file pyproject.toml
pytest tests -q --cov=chorusgraph --cov=benchmark

# Load envelope (E7)
python -m benchmark.load --requests 40 --levels 1,2,4,8

# Deploy smoke (E8)
cd deploy; docker compose up --build
curl http://localhost:8080/health
```

See [`handoffs/handoffEback.md`](../handoffs/handoffEback.md) for full E1–E9 return details.

*Updated 2026-07-05 — post-merge enterprise track complete.*
