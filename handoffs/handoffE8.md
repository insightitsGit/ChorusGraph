# Handoff E8 — Deployment & Packaging

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/ENTERPRISE_READINESS.md`](../docs/ENTERPRISE_READINESS.md) **§E8** · [`../docs/PROCESS.md`](../docs/PROCESS.md).
**Depends on:** E1, E3, E5. **Return in:** `handoffs/handoffbackE8.md`.

## 0. Operating rules
No fakes; recorded fixtures for tests. One bounded increment. A clean-room deploy must work from the docs alone.

## 1. Goal
A clean deploy from scratch on a fresh environment via **documented steps** — the "point it at one Postgres" story, productized.

## 2. Deliverables
- **Product Dockerfile(s)** + deployment manifests (k8s / helm; ChorusMesh for transport if used).
- **12-factor config management** — everything env-driven; dev/staging/prod separation; secrets via vault/env (no hardcoding).
- **Install story productized** — "point ChorusGraph at one Postgres" documented end-to-end.

## 3. Out of scope
E1–E7 · E9 · MVP fixes · new features.

## 4. Acceptance criteria
- [ ] A **clean deploy from scratch** on a fresh environment via documented steps succeeds.
- [ ] All config is environment-driven; **no hardcoded secrets** (verified by the E3 secrets-scan).
- [ ] The one-Postgres install path works and is documented.
- [ ] Deterministic tests green (E1).

## 5. Open questions for handoffbackE8
1. Orchestration target (k8s / docker-compose) and why.
2. Config approach (env / config file / vault).
3. Anything that resisted clean-room deploy (hidden local dependency).
4. Proposed E9 scope.

## 6. Return format
Summary · file tree · how to run (the clean-room deploy steps) · decisions/deviations · blockers · answers to §5 · proposed E9.

---
*Handoff E8 · enterprise track · deployment + packaging · clean-room deploy from docs.*
