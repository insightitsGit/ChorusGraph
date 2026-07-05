# Handoff E1 — Engineering Foundation (CI + deterministic tests + quality gates)

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/ENTERPRISE_READINESS.md`](../docs/ENTERPRISE_READINESS.md) **§E1** · process: [`../docs/PROCESS.md`](../docs/PROCESS.md).
**Return in:** `handoffs/handoffbackE1.md`.

First enterprise-track handoff. Foundation-first: CI + a test tier that runs **without live keys** is the
ground every later phase (E2–E9) stands on. No product features here — engineering hygiene only.

**Track gate: cleared.** The MVP is complete (native engine: Send, subgraphs, per-node durability,
Command/interrupt, distribution + federation wired) and the benchmark result is in hand — full
8-scenario matrix (`azure_20260704_212111`, verified against raw JSONL): finance clean sweep,
healthcare-single tie, healthcare-multi +30pp win, zero errors. This is genuinely the first
enterprise-track handoff, not a parallel-track exception.

---

## 0. Operating rules
- **No fakes — and recorded fixtures are NOT fakes.** The deterministic tier records **real** Gemini/tool
  responses once, then replays them. That honors "no fakes" (the data is real, captured) while making CI
  fast and keyless. Do **not** hand-write fabricated responses.
- Behavior-preserving: existing tests must keep passing.

## 1. Goal
Make the codebase CI-ready: the full suite runs green **with no secrets**, quality gates (lint/type/format/
coverage) are enforced on every PR, dependencies are pinned, and a release is reproducible.

## 2. Deliverables (scope — exactly E1)

### 2.1 Deterministic test tier (the keystone)
- Record real Gemini + real tool (Frankfurter) responses as **fixtures/cassettes** (e.g. `vcrpy` or an
  equivalent recorder), stored in-repo.
- The default `pytest` run replays fixtures — **no `GEMINI_API_KEY`, no network, fast (seconds).**
- Keep the **live-integration tests behind a marker/flag** (e.g. `-m live`) that only runs on demand with
  a real key. So: `pytest` = fast+keyless (CI); `pytest -m live` = the current real-API suite.

### 2.2 CI pipeline — `.github/workflows/ci.yml`
- On every PR + push: install, run the **deterministic** suite, lint, type-check, coverage — **no secrets**.
- Optionally a separate, manual/scheduled `live` job that uses a repo-secret key (not on every PR).

### 2.3 Quality gates
- **Lint:** `ruff` configured + passing.
- **Format:** `black` (or `ruff format`) — check mode in CI.
- **Type-check:** `mypy` on the package (start lenient if needed; record the baseline; no new `# type: ignore` without reason).
- **Coverage:** measured, reported in CI, with a **floor** (set it to the current level so it can only go up).

### 2.4 Dependency + release hygiene
- **Lockfile / pinned versions** (e.g. `pip-tools` / `uv` lock or pinned `pyproject`), committed.
- **SBOM** generated (e.g. `cyclonedx`) — one file in-repo or CI artifact.
- **Release process:** semver already in use; add a `CHANGELOG.md` and a documented tagged-release step.

## 3. Explicitly OUT of scope
Everything E2–E9 (resilience, security, observability, persistence, multi-tenant, perf/load, deployment,
API 1.0) · the MVP H10 fixes (routing bug, rubric, volume rerun) · any new product feature · changing
runtime behavior.

## 4. Acceptance criteria
- [ ] `pytest` (default) runs the full suite **green with no `GEMINI_API_KEY` and no network**, in seconds.
- [ ] `pytest -m live` still runs the real-API tests (unchanged) behind the flag.
- [ ] CI workflow runs deterministic suite + ruff + mypy + coverage on a PR, **with no secrets**, and passes.
- [ ] Coverage reported with a floor that fails CI if it drops.
- [ ] Lockfile committed; `pip install` from it is reproducible; SBOM produced.
- [ ] `CHANGELOG.md` exists + a documented tag/release step.
- [ ] No runtime behavior changed; no fabricated (non-recorded) test data.

## 5. Open questions for handoffbackE1
1. Fixture mechanism chosen (`vcrpy` vs custom recorder) and why; how Gemini + Frankfurter recordings are stored/scrubbed of any sensitive data.
2. Current coverage number (the floor you set).
3. `mypy` baseline — how many existing issues; strict or lenient to start?
4. Anything in the code that resisted keyless testing (global state, real DB, etc.).
5. Proposed E2 scope (resilience).

## 6. Return format
Same as MVP handoffs: summary · file tree · how to run (**show the keyless `pytest` running green**) ·
CI run result · decisions/deviations · blockers · answers to §5 · proposed E2 scope.

---
*Handoff E1 · architect: Claude · enterprise track · foundation-first · keyless CI + quality gates · no runtime changes.*
