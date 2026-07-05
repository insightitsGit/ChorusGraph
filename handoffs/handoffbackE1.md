# Handoffback E1 — Engineering Foundation

**Status:** Complete on branch `P1_Enterprice1`  
**Commit:** (see git log)

## Summary

E1 delivers a **keyless, network-free default test tier** for CI, quality gates (ruff/mypy/coverage), GitHub Actions workflow, lockfile snapshot, SBOM generation, and release documentation. No production runtime behavior changed.

## File tree (new/changed)

```
.github/workflows/ci.yml
CHANGELOG.md
docs/RELEASE.md
pyproject.toml                    # dev deps, pytest/ruff/mypy/coverage config
requirements-lock.txt             # pinned snapshot of core deps
tests/conftest.py                 # deterministic vs live markers
tests/support/deterministic.py    # cassette replay + Gemini stub
tests/support/stub_gemini.py
tests/fixtures/cassettes/frankfurter/*.json
tests/test_deterministic_tier.py
handoffs/handoffbackE1.md
```

## How to run

```powershell
# Default (CI) — no GEMINI_API_KEY, no network, ~16s
pytest

# Live integration (real Gemini + Frankfurter)
$env:CHORUSGRAPH_LIVE = "1"
$env:GEMINI_API_KEY = "your-key"
pytest -m live
```

**Latest deterministic run:** `286 passed, 4 skipped, 9 deselected (live), 16s`

## Decisions

| Topic | Choice | Why |
|-------|--------|-----|
| Fixture mechanism | **Custom JSON cassettes** + httpx.Client patch | Frankfurter only; simpler than vcrpy for two endpoints; real recorded payloads |
| Gemini in CI | **DeterministicGeminiStub** via pytest_configure patches | Avoids .env key discovery; HC1/FC runners construct clients at import/init |
| Live tests | `@pytest.mark.live` + `addopts = "-m 'not live'"` | Default pytest excludes 9 live tests |
| Ruff scope | **tests/ + .github/** for CI pass | Legacy chorusgraph/ has 2300+ pre-existing ruff findings — full-package lint deferred to incremental cleanup |
| Coverage floor | **71%** | Measured ~72% on full suite; floor set one point below to prevent regression |
| Mypy | **Lenient baseline** (`ignore_missing_imports=true`) | Records baseline without blocking on prismlang/cortex stubs |

## Answers to handoff §5

1. **Fixtures:** Custom recorder under `tests/fixtures/cassettes/`; Frankfurter USD/EUR, EUR/GBP, USD/GBP recorded 2026-07-03 from api.frankfurter.app. No secrets in cassettes.
2. **Coverage floor:** 71% (`fail_under` in pyproject.toml).
3. **Mypy:** Lenient — `ignore_missing_imports`, no `disallow_untyped_defs`; chorusgraph-only in CI.
4. **Keyless resistors:** `.env` auto-discovery in `resolve_gemini_api_key()`; runner `__init__` eagerly building `InstrumentedGeminiClient`; stub subclasses calling `InstrumentedGeminiClient().usage` (fixed to `LlmUsage()`).
5. **Proposed E2 scope:** Timeouts/retries/breakers on Gemini, tools, DB, Cortex; fault-injection test; typed partial results in Route Ledger.

## Blockers

None for E1.

## Next

**E2 — Resilience** on `P1_Enterprice1` (separate commit after E1).
