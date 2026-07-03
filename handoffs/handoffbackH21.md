# Handoff back H21 — CacheProfile implementation

**Date:** 2026-07-03 · **Engineer:** Cursor

---

## T1 — CacheProfile schema + registry ✅

**Files:** `chorusgraph/sections/models.py`, `chorusgraph/sections/profiles.py`, `chorusgraph/sections/profiles.default.json`, `tests/test_cache_profiles.py`

**Exit:** `python -m pytest tests/test_cache_profiles.py -q` → 3 passed

---

## T2 — Gate + interceptor honor profile ✅

**Files:** `chorusgraph/cache_gate/gate.py`, `sidecar.py`, `backend.py`, `scope.py`, `chorusgraph/core/cache_interceptor.py`, `tests/test_cache_gate_profile.py`

**Exit:** `python -m pytest tests/test_cache_gate_profile.py -q` → 4 passed (scope isolation, TTL expiry, fingerprint keying, high-risk verify)

---

## T3 — Clinical fingerprint keying ✅

**Files:** `benchmark/healthcare/fingerprint.py`, `tests/test_clinical_fingerprint.py`

**Exit:** paraphrase same fingerprint; drug/lab delta different fingerprint — 3 passed

---

## T4 — Quality-gated seeding ✅

**Files:** `chorusgraph/cache_gate/seed_policy.py`, `benchmark/shared/healthcare_cache.py`, `tests/test_seed_policy.py`

**Exit:** refusal/abstain/safety gating — 5 passed

---

## T5 — HC1 shared cache + offline proof ✅ (revised)

**Files:** `benchmark/hc1/runner.py` (`_shared_runtime`), `benchmark/hc2/runner.py`, `benchmark/hc2/nodes.py`, `benchmark/hc2/cache_helpers.py`, `tests/test_hc1_cache_scope.py`

**Proof method:**
- Real `build_healthcare_graph_hc1` via `HC1Runner` — only `InstrumentedGeminiClient` stubbed
- Pass 1: full 18-case workload (`seed=42`, `repeat_band_pct=40`) warms global facts cache
- Pass 2: 8 cross-session repeat/paraphrase rows (new `session_id`) — seedable canonicals only (abstain cases excluded)
- Strict assertions: `cache_hit is True`, `llm_calls == 1` (writer-only), `llm_calls < cold baseline` — no vacuous `or`
- Negative: `test_judgment_fingerprint_miss_across_different_fingerprints` — different fingerprint ⇒ miss

**HC1 offline hit rate (pass 2 cross-session repeats):** **100%** (8/8 rows)

**Exit:** `python -m pytest tests/test_hc1_cache_scope.py -q` → 2 passed

---

## T6 — Profiler ✅

**Files:** `benchmark/profiler.py`, `benchmark/run_profiler.py`, `benchmark/fixtures/profiler/*.json`, `tests/test_profiler.py`

**Command:**
```
python -m benchmark.run_profiler --run-id h21_offline
```

**Output (h21_offline):**
| slug | keying | ttl_s | scope | risk |
|------|--------|-------|-------|------|
| fx_rates | semantic | 86400 | global | low |
| clinical_guidelines | fingerprint | null | session | high |

Evidence: `benchmark/results/profiler/h21_offline/profiler_manifest.json`

**Exit:** `python -m pytest tests/test_profiler.py -q` → 3 passed

---

## T7 — Docs ✅

- `docs/DESIGN_v0.3_PRISM_ENGINE.md` §4.2 — cross-link to CACHE_PROFILES
- `docs/BENCHMARK.md` — CacheProfile disclosure requirement
- `benchmark/SCENARIOS.md` — per-scenario profile table + archetype C cache proof note

---

## Full suite

```
python -m pytest tests/ -q
206 passed, 3 skipped in ~64s
```

---

## Deviations from spec

None on schema. Profiler uses `semantic_close` flag on delta probes in fixtures to distinguish entity-change deltas (FX currency pair) from semantically-close clinical deltas (K+ shift) — aligns with CACHE_PROFILES §6 sensitivity probe intent.

---

## Not done (explicit non-goals per H21)

- Azure matrix re-run
- FC1/FC2/HC2 migration to core engine (P7)

---

*H21 complete · committed in two steps (engine checkpoint + T5 proof)*
