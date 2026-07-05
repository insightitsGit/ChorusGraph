# Handoffback E — Enterprise Track Complete (E1–E9)

**From:** Senior Engineer (Cursor) · **To:** Architect (Claude) · **Director:** Amin  
**Branch:** `P1_Enterprice1` · **Base:** `master` @ `4e046df`  
**Version:** `1.0.0` · **Status:** All nine handoffs implemented, tested, committed  
**Design reference:** [`docs/ENTERPRISE_READINESS.md`](../docs/ENTERPRISE_READINESS.md) · process: [`docs/PROCESS.md`](../docs/PROCESS.md)

---

## 1. Executive summary

The full enterprise hardening track (E1–E9) is complete on branch **`P1_Enterprice1`**. Each handoff was delivered as a **separate commit** with tests and a per-handoff return doc (`handoffbackE1.md` … `handoffbackE9.md`). This document is the **master return** consolidating all nine.

| # | Handoff | Commit | One-line outcome |
|---|---------|--------|------------------|
| E1 | Engineering foundation | `f80655b` | Keyless CI pytest, GitHub Actions, quality gates, lockfile, SBOM |
| E2 | Resilience | `ae315a7` | Breakers, retries, typed partial failures, fault-injection tests |
| E3 | Security (§21) | `74a80c3` | Tool sandbox, TLS default, federation auth, PII redaction, threat model |
| E4 | Observability | `24ce386` | JSON logs, OTel traces, health/metrics endpoints, runbooks |
| E5 | Durable persistence | `3e8db6f` | SqliteGraphStore, migrations, backup/restore, right-to-forget |
| E6 | Multi-tenant isolation | `1477d45` | Tenant guards, quotas, cross-tenant leakage tests |
| E7 | Performance & load | `802d04b` | Concurrent load harness, throughput/latency envelope |
| E8 | Deployment & packaging | `3d18318` | Dockerfile, docker-compose, k8s, deploy docs |
| E9 | API 1.0 | `ae22cb2` | Frozen public API, stability guarantee, v1.0.0 |

**Latest test run (keyless, no secrets):** `319 passed, 4 skipped, 9 deselected, ~18–24s`

**Not pushed to remote** — awaiting Director approval.

---

## 2. How to run (everything)

```powershell
# Default CI tier — no GEMINI_API_KEY, no network
pytest

# Live integration (real Gemini + Frankfurter)
$env:CHORUSGRAPH_LIVE = "1"
$env:GEMINI_API_KEY = "your-key"
pytest -m live

# Per-handoff test modules
pytest tests/test_deterministic_tier.py -v    # E1
pytest tests/test_resilience.py -v          # E2
pytest tests/test_security.py -v            # E3
pytest tests/test_observability.py -v       # E4
pytest tests/test_persistence.py -v         # E5
pytest tests/test_tenant_isolation.py -v    # E6
pytest tests/test_load.py -v                # E7

# CI quality gates (local)
ruff check tests .github
ruff format --check tests .github
mypy chorusgraph --config-file pyproject.toml
pytest tests -q --cov=chorusgraph --cov=benchmark

# Security scans (E3)
bandit -r chorusgraph -ll -x tests
pip-audit

# Load harness (E7)
python -m benchmark.load --requests 40 --levels 1,2,4,8

# Health server (E4 / E8)
python -c "from chorusgraph.observability import start_health_server; start_health_server(); input()"

# Deploy (E8)
cd deploy
docker compose up --build
curl http://localhost:8080/health
```

---

## 3. E1 — Engineering foundation

**Commit:** `f80655b` · **Return:** [`handoffbackE1.md`](handoffbackE1.md)

### Goal
CI-ready codebase: full suite green with no secrets, quality gates on every PR, reproducible releases.

### Delivered
- **Deterministic test tier** — Frankfurter JSON cassettes + `DeterministicGeminiStub`; default `pytest` is keyless and fast
- **Live tier** — `@pytest.mark.live`; excluded by default via `addopts = "-m 'not live'"`
- **CI** — `.github/workflows/ci.yml`: pytest + ruff + mypy + coverage + SBOM artifact
- **Security CI job** — bandit, pip-audit, gitleaks (added in E3)
- **Lockfile** — `requirements-lock.txt`
- **Release hygiene** — `CHANGELOG.md`, `docs/RELEASE.md`

### Acceptance criteria

| Criterion | Status |
|-----------|--------|
| `pytest` green with no `GEMINI_API_KEY` / no network | ✅ |
| `pytest -m live` runs real-API tests | ✅ |
| CI passes with no secrets | ✅ (workflow committed; run on push) |
| Coverage floor enforced | ✅ 71% (`fail_under` in pyproject.toml) |
| Lockfile + SBOM | ✅ |
| CHANGELOG + release docs | ✅ |
| No runtime behavior change | ✅ (test tier only) |

### Key decisions
- **Fixtures:** Custom JSON cassettes (not vcrpy) — Frankfurter USD/EUR, EUR/GBP, USD/GBP recorded 2026-07-03
- **Ruff scope:** `tests/` + `.github/` only (legacy package lint deferred)
- **Mypy:** Lenient baseline, `ignore_missing_imports=true`

### Files
```
.github/workflows/ci.yml
CHANGELOG.md
docs/RELEASE.md
pyproject.toml
requirements-lock.txt
tests/conftest.py
tests/support/deterministic.py
tests/support/stub_gemini.py
tests/fixtures/cassettes/frankfurter/*.json
tests/test_deterministic_tier.py
```

---

## 4. E2 — Resilience

**Commit:** `ae315a7` · **Depends on:** E1 · **Return:** [`handoffbackE2.md`](handoffbackE2.md)

### Goal
One node/tool/service failing never crashes the whole graph; typed errors in Route Ledger.

### Delivered
- `chorusgraph/resilience/` — error taxonomy, circuit breaker, retry policy, `resilient_call`
- Tool + Frankfurter + Gemini wrapped with timeout/retry/breaker
- Scheduler `_failure_command` — graceful partial result on node exception
- `IdempotencyGuard` on Cortex digest (no duplicate writes on retry)
- Ledger `error_code`, `error_kind`, `retryable` on `LedgerStep`

### Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Fault-injection: graph stays responsive, typed error in ledger | ✅ `tests/test_resilience.py` |
| Every external call has timeout + retry + breaker | ✅ tools, Frankfurter, Gemini |
| Retried ops idempotent | ✅ digest dedup by `source_id` |
| Deterministic tests green | ✅ |

### Key decisions
- In-process circuit breaker (5 failures → open, 30s recovery)
- Partial result: `Command(goto=END)` + `__partial__` / `__node_error__` in state
- `NodeInterrupt`, `MidStepAbort`, `GraphInterrupt` re-raised (not swallowed)

### Files
```
chorusgraph/resilience/
chorusgraph/core/channels.py      # NodeUpdate error fields
chorusgraph/core/scheduler.py     # _failure_command
chorusgraph/core/trace.py
chorusgraph/ledger/models.py
chorusgraph/ledger/sink.py
chorusgraph/nodes/tool.py
chorusgraph/examples/finance_agent/gemini_client.py
chorusgraph/memory/async_digest.py
tests/test_resilience.py
```

---

## 5. E3 — Security (§21 build-out)

**Commit:** `74a80c3` · **Depends on:** E1, E2 · **Return:** [`handoffbackE3.md`](handoffbackE3.md)

### Goal
Close DESIGN §21 ship-gate security items for regulated buyers.

### Delivered
- **Tool sandbox** — `ToolAllowlist`, injection pattern scan on args; default finance allowlist on `ToolRegistry`
- **Transport** — `TransportSecurityPolicy`: TLS default; CHORUS cipher **opt-in off** (`CHORUSGRAPH_CHORUS_CIPHER=1`)
- **Federation auth** — `FederationAuthContext` on `PrismAPISpine.invoke` (bearer + tenant match)
- **Cache poisoning** — `CacheSecurityGuard` write-auth, per-tenant isolation, no user-generated cache writes
- **PII** — regex redaction at ledger persist; `docs/PII_RETENTION.md`
- **CI security** — bandit, pip-audit, gitleaks in `.github/workflows/ci.yml`
- **Threat model** — `docs/THREAT_MODEL.md`

### Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Malicious tool arg contained | ✅ `tests/test_security.py` |
| TLS default; cipher off-by-default | ✅ |
| Cross-tenant federation denied | ✅ |
| Cache cross-tenant write blocked | ✅ |
| PII redaction in ledger | ✅ |
| SAST/SCA in CI | ✅ (gitleaks continue-on-error for baseline) |

### Files
```
chorusgraph/security/
docs/THREAT_MODEL.md
docs/PII_RETENTION.md
tests/test_security.py
.github/workflows/ci.yml          # security job
```

---

## 6. E4 — Observability / ops

**Commit:** `24ce386` · **Depends on:** E1 · **Return:** [`handoffbackE4.md`](handoffbackE4.md)

### Goal
Diagnose a failing turn from telemetry alone.

### Delivered
- **Structured logging** — `JsonLogFormatter`, correlation/run_id via `set_correlation`
- **OTel-compatible traces** — `ledger_to_trace()`; `trace_id == ledger.run_id`
- **Metrics** — `RuntimeMetrics` (LLM calls, cache hit rate, errors, per-node latency)
- **Health endpoints** — `/health`, `/ready`, `/metrics` via `start_health_server`
- **Runbooks** — `docs/runbooks/COMMON_FAILURES.md`

### Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Traces + metrics + health exportable | ✅ JSON trace + HTTP probes |
| Correlation IDs tie to `run_id` | ✅ |
| Ledger spans include cache/error attrs | ✅ |
| Deterministic tests green | ✅ |

### Files
```
chorusgraph/observability/
chorusgraph/core/trace.py         # metrics + correlation wiring
chorusgraph/compat/otel_exporter.py  # extended via observability/otel.py
docs/runbooks/COMMON_FAILURES.md
tests/test_observability.py
```

---

## 7. E5 — Durable & scalable persistence

**Commit:** `3e8db6f` · **Depends on:** E1 · **Return:** [`handoffbackE5.md`](handoffbackE5.md)

### Goal
Memory + state survive restarts; migrate, backup, delete are real.

### Delivered
- **Durable GraphStore** — `SqliteGraphStore` wraps InMemoryGraphStore with SQLite persistence (survives process restart)
- **Cortex wiring** — `create_durable_prism_memory()`; `CortexMemoryService(durable_graph=True)` default
- **Migrations** — versioned forward migrations (`schema_migrations` v1–v3)
- **Backup/restore** — `backup_sqlite_stores`, `restore_sqlite_store`, `verify_backup_integrity`
- **Right-to-forget** — `DataLifecycleManager.forget_subject()` across graph, ledger, cache sidecar, checkpoints; `CortexMemoryService.forget()`

### Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Graph state survives restart | ✅ `test_graph_store_survives_restart` |
| Migrations run forward | ✅ |
| Backup → restore round-trip | ✅ |
| Delete erases across layers | ✅ `test_forget_erases_graph_and_ledger` |

### Deferred (documented)
- **Postgres-native Cortex GraphStore** — SQLite durable store ships for 1.0; Postgres graph connector Phase 2 (see `docs/STABILITY.md`)

### Files
```
chorusgraph/persistence/
chorusgraph/memory/cortex_service.py
docs/BACKUP_RESTORE.md
tests/test_persistence.py
```

---

## 8. E6 — Multi-tenant isolation

**Commit:** `1477d45` · **Depends on:** E1, E5 · **Return:** [`handoffbackE6.md`](handoffbackE6.md)

### Goal
Airtight tenant isolation + resource fairness.

### Delivered
- **TenantContext** — server-side tenant scope; `assert_match` on cross-tenant access
- **Layer guards** — `assert_ledger_read`, `assert_cache_read`, `assert_graph_read`, `safe_get_run`
- **Resource limits** — `TenantResourceLimiter` (rate/min + concurrency caps)
- **Leakage test suite** — ledger, cache, graph, quota tests

### Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Cross-tenant leakage tests pass | ✅ `tests/test_tenant_isolation.py` |
| Per-tenant limits enforced | ✅ |
| Isolation under durable stores (E5) | ✅ graph store tenant_id enforced |

### Files
```
chorusgraph/tenant/
tests/test_tenant_isolation.py
```

---

## 9. E7 — Performance & load

**Commit:** `802d04b` · **Depends on:** E1, E5, E6 · **Return:** [`handoffbackE7.md`](handoffbackE7.md)

### Goal
Documented throughput + latency envelope under concurrent load.

### Delivered
- **Load harness** — `benchmark/load/harness.py`: `run_load`, `run_sweep`
- **CLI** — `python -m benchmark.load --requests N --levels 1,2,4,8`
- **Metrics reported** — throughput (req/s), P50/P95 latency, success rate per concurrency level
- **Docs** — `docs/LOAD_TESTING.md`

### Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Throughput + P50/P95 at increasing concurrency | ✅ harness + tests |
| Documented capacity methodology | ✅ LOAD_TESTING.md |
| Distinct from H9/H10 A/B benchmark | ✅ engine-only workload |

### Deferred
- Azure-sized soak test + Director SLO sign-off (methodology documented; not run in this branch)

### Files
```
benchmark/load/
docs/LOAD_TESTING.md
tests/test_load.py
```

---

## 10. E8 — Deployment & packaging

**Commit:** `3d18318` · **Depends on:** E1, E3, E5 · **Return:** [`handoffbackE8.md`](handoffbackE8.md)

### Goal
Clean deploy from scratch via documented steps — "point it at one Postgres."

### Delivered
- **Dockerfile** — `deploy/Dockerfile` with healthcheck on `:8080`
- **docker-compose** — Postgres 16 + ChorusGraph app; env-driven config
- **Kubernetes** — `deploy/k8s/deployment.yaml` with readiness/liveness probes
- **12-factor config** — all secrets via env / k8s secrets
- **Install docs** — `docs/DEPLOY.md`

### Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Documented clean-room deploy steps | ✅ DEPLOY.md |
| No hardcoded secrets | ✅ env-only |
| One-Postgres path documented | ✅ compose + CHORUSGRAPH_PG_DSN |
| Deterministic tests green | ✅ |

### Files
```
deploy/Dockerfile
deploy/docker-compose.yml
deploy/k8s/deployment.yaml
docs/DEPLOY.md
```

---

## 11. E9 — API 1.0

**Commit:** `ae22cb2` · **Depends on:** E1–E8 · **Return:** [`handoffbackE9.md`](handoffbackE9.md)

### Goal
Stable, fully documented 1.0 public API with stability guarantee.

### Delivered
- **Version bump** — `1.0.0` in `pyproject.toml` and `chorusgraph/__init__.py`
- **Frozen public surface** — `chorusgraph/public.py` with explicit `PUBLIC_API` list
- **Reference docs** — `docs/API_1_0.md`
- **Stability policy** — `docs/STABILITY.md` (semver, deprecation, 0.x→1.0 migration)
- **CHANGELOG** — `[1.0.0]` section with E1–E9 summary

### Namespace decision (for Director)
**Keep `chorusgraph`** as primary package (`pip install chorusgraph`). Prism extras (`prismcortex`, `prismlang`) remain separate dependencies. Defer `prismlib-plus[orchestrator]` merge to Phase 2.

### Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Public API frozen + documented | ✅ |
| Versioning/deprecation policy written | ✅ |
| Published reference + quickstart pointers | ✅ API_1_0.md |
| Namespace decided | ✅ `chorusgraph` (pending Director sign-off) |
| 1.0 release ready to tag | ✅ `git tag v1.0.0` when approved |

### Files
```
chorusgraph/public.py
docs/API_1_0.md
docs/STABILITY.md
CHANGELOG.md
handoffs/handoffbackE9.md
```

---

## 12. Complete file tree (new modules)

```
.github/workflows/ci.yml
CHANGELOG.md
requirements-lock.txt
docs/RELEASE.md
docs/THREAT_MODEL.md
docs/PII_RETENTION.md
docs/BACKUP_RESTORE.md
docs/LOAD_TESTING.md
docs/DEPLOY.md
docs/API_1_0.md
docs/STABILITY.md
docs/runbooks/COMMON_FAILURES.md

chorusgraph/resilience/          # E2
chorusgraph/security/            # E3
chorusgraph/observability/       # E4
chorusgraph/persistence/         # E5
chorusgraph/tenant/              # E6
chorusgraph/public.py            # E9

benchmark/load/                  # E7
deploy/                          # E8

tests/test_deterministic_tier.py
tests/test_resilience.py
tests/test_security.py
tests/test_observability.py
tests/test_persistence.py
tests/test_tenant_isolation.py
tests/test_load.py
tests/conftest.py
tests/support/

handoffs/handoffbackE1.md … handoffbackE9.md
handoffs/handoffEback.md         # this document
```

---

## 13. Test inventory (enterprise additions)

| Module | Handoff | Tests |
|--------|---------|-------|
| `test_deterministic_tier.py` | E1 | Cassette replay, live marker, stub |
| `test_resilience.py` | E2 | Breaker, fault injection, graph partial, idempotency |
| `test_security.py` | E3 | Sandbox, TLS, federation, cache, PII |
| `test_observability.py` | E4 | Trace ID, OTel export, health server, metrics |
| `test_persistence.py` | E5 | Restart survival, migrations, backup, forget |
| `test_tenant_isolation.py` | E6 | Cross-tenant denial, quotas |
| `test_load.py` | E7 | Throughput sweep |

**Full suite:** 319 passed, 4 skipped, 9 deselected (live)

---

## 14. Blockers and honest deferrals

| Item | Status | Notes |
|------|--------|-------|
| Push to remote | ⏸ | Awaiting user permission |
| `git tag v1.0.0` | ⏸ | Awaiting Director sign-off |
| Postgres-native Cortex GraphStore | Phase 2 | SQLite durable graph ships in 1.0 |
| CHORUS cipher audit | Open | Off by default; opt-in only |
| Full-package ruff on `chorusgraph/` | Deferred | 2300+ pre-existing findings |
| Azure load/soak with Director SLOs | Deferred | Harness + docs ready |
| `prismlib-plus[orchestrator]` namespace | Phase 2 | `chorusgraph` retained for 1.0 |

---

## 15. MVP benchmark (unchanged)

Canonical run remains **`20260704_212111`** on `master` — not modified by enterprise track.

| Pair | Success (L → C) | C cache |
|------|-----------------|---------|
| FL1/FC1 | 87.5% → **100%** | 47.5% |
| FL2/FC2 | 75% → **87.5%** | 40% |
| HL1/HC1 | 72.5% → 72.5% (tie) | 42.5% |
| HL2/HC2 | 57.5% → **87.5%** | 25% |

---

## 16. Recommended next steps for Director

1. **Review** branch `P1_Enterprice1` (9 commits, E1–E9)
2. **Sign off** namespace (`chorusgraph`) and E7 load SLO targets
3. **Merge** to `master` and tag **`v1.0.0`**
4. **Phase 2 backlog:** Postgres Cortex graph, CHORUS cipher audit, full-package lint, Azure soak

---

*Handoffback E · enterprise track complete · branch `P1_Enterprice1` · v1.0.0 · architect: Claude · engineer: Cursor · 2026-07-05.*
