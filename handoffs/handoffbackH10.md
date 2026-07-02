# Handoff H10 — Return · Engineer → Director (Amin) · Consultant onboarding

**Date:** 2026-07-02 (updated with Director sign-off)  
**Director:** Amin  
**Status:** **Director MVP close — fixes validated.** Pilot benchmark complete; architect literal volume spec partially met (optional follow-up only).  
**Director verdict:** **Overall fixes worked.** FX path is **good and effective** on ChorusGraph (B). Safe for pilots and consultant handoff.  
**Canonical results run:** `benchmark/results/h10_slices_pilot_60` (60 tasks, band 40%, post-fix code).  
**Public doc:** [`docs/BENCHMARK_RESULTS.md`](../docs/BENCHMARK_RESULTS.md)  
**Archived fixtures:** `tests/fixtures/benchmark_results/MANIFEST.json`

---

## 0. Context for the consultant (read this first)

### Who did what

| Role | Status |
|------|--------|
| **Architect (Claude)** | Authored `handoffH10.md` and early H9 design. **Director excluded from active work** after implementation mistakes (e.g. inflated LLM call paths, benchmark methodology gaps). Do not treat architect handoffs as automatically current. |
| **Engineering (Cursor agent)** | Shipped defect fixes, cache wiring, memory workload, slice reporting, and validation pilots under **Director operating rules** (no fakes, honest wins/losses). |
| **Director (Amin)** | Owns fairness sign-off, release tag, and what claims go external. Chose **not** to require full architect H10 (3×1000 all bands on Azure) before MVP/pilots. |

### What this project is proving

**Container A** = competent **LangGraph** ReAct finance agent (baseline).  
**Container B** = **ChorusGraph** (semantic cache, Cortex memory, template writer, compound fast path, AgentNode ReAct).

The benchmark is **not** “same code path with cache on/off.” It isolates **framework capabilities** vs a fair LangGraph baseline. See [`benchmark/FAIRNESS_H9.md`](../benchmark/FAIRNESS_H9.md).

### Critical data hygiene

| Run | Tasks | Valid for cache thesis? | Notes |
|-----|-------|-------------------------|-------|
| `h10_volume` (bands 40+60) | 1000 each | **NO** | Pre **cache-seed fix** → **0% cache hits**. Still useful for A vs B latency/accuracy at volume **without** cache. |
| `h10_slices_pilot_60` | 60 | **YES** | **Canonical post-fix** — use for cache, memory, slices, belief calibration. |
| `cache_seed_pilot_40`, `h10_final_pilot_40` | 40 | YES (smaller n) | Earlier validation pilots. |

**Rule:** Never cite `h10_volume` cache_hit_rate (0%) as evidence that cache fails.

---

## 1. Executive summary

### Director sign-off (Amin, 2026-07-02)

> **The overall fix set worked.** Cache, memory, rubric, compound routing, and reporting all behave as intended on the canonical post-fix pilot. **FX on ChorusGraph (B) is good and effective** for pilots and technical sales. LangGraph (A) remains a **real, weaker baseline** on FX (~27% on FX-only slice) — that is expected asymmetry, not a benchmark bug.  
> **Do not block MVP** on post-fix 1000×3 volume or git tag unless we want publication-grade stats or a formal release marker.

### Fix validation — before vs after

| Area | Before fixes | After fixes (`h10_slices_pilot_60`) | Verdict |
|------|--------------|-------------------------------------|---------|
| Cache hit-rate | **0%** (ReAct never seeded) | **41%** full / **49%** FX; **100%** exact repeat | ✅ **Worked** |
| Cache on hit | N/A | 0 LLM calls, ~sub-20 ms | ✅ **Worked** |
| Paraphrase cache | ~14% (pre multi-phrase seed) | **67%** (6/9) | ✅ **Worked** |
| `cache_score` / belief | Null | `confidence_stop=1.0`, 51 samples | ✅ **Worked** |
| Cross-session memory | Not tested / demo fallback | B **5/5** vs A **2/5** (n=5) | ✅ **Worked** |
| FX task success (B) | — | **82%** [74%, 91%] FX-only | ✅ **Good & effective** |
| Sliced reporting | Misleading “A=35%” headline | FX / memory / full tables | ✅ **Worked** |

| H10 deliverable | Status |
|-----------------|--------|
| §2.1 Compound routing | ✅ `compound_tool` fast path + ReAct compound intent |
| §2.2 Grounded canonical rubric | ✅ `benchmark/rubric.py` + `canonical_id` |
| §2.3 Cache-exercising workload | ✅ Bands 20/40/60 model; **+ memory tasks** (seed + cross-session recall) |
| §2.4 Fairness disclosure | ✅ `FAIRNESS_H9.md` §3 — B features documented, not hidden |
| §2.5 Volume run all bands ≥1000 + CIs | ⚠️ **Partial** — `h10_volume` 1000× bands 40+60 (pre-cache-fix); band 20 not in that run; **no Azure**; post-fix volume not rerun |
| §2.6 Belief calibration | ✅ Populated on pilot (`confidence_stop`, `groundedness_floor`); **small n**, not production-enabled |
| §2.7 Recall generalization | ✅ Demo `"risk tolerance"` fallback **removed** from `recall_for_turn` / `recall_structured` |
| §2.8 Docs + tag | ⚠️ `BENCHMARK_RESULTS.md` updated; **git tag v0.9.1 not applied**; DESIGN §6–7 vector boundary doc **not** expanded in this pass |

### Cache thesis (H10 open question #1)

**Director answer: YES — cache earns its overhead at ~40% repeat (pilot validated).**

- B cache hit-rate: **41.4%** [28.6%, 54.2%] (full workload)
- B exact_repeat FX cache: **100%** (16/16)
- B paraphrase FX cache: **67%** (6/9) after canonical phrase seeding
- Paired latency delta: **−967 ms** [−1422, −494] (B faster)
- Paired cost delta: **−$0.000052/task** [−$0.000088, −$0.000015] (B cheaper)

**Conclusion:** Cache **does** earn overhead — skips ReAct on hit (0 LLM, sub-20 ms). **FX is the strongest slice** (~82% B accuracy, ~49% cache on FX tasks). Optional: 300-task band-60 rerun for tighter CIs only; not required to claim pilot success.

### MVP done?

**Director MVP: YES — closed for pilots and honest external claims** (use sliced metrics; canonical run `h10_slices_pilot_60`).  
**Architect H10 literal:** Partial — post-fix 1000×3 bands, Azure, git tag are **optional polish**, not blockers per Director.

---

## 2. Answers to handoffH10 §5 (open questions)

### 2.1 Does the cache deliver at 40%/60% repeat?

| Evidence | Band | Cache hit-rate | Verdict |
|----------|------|----------------|---------|
| `h10_slices_pilot_60` (post-fix) | 40% | **41.4%** CI above | **Yes, pilot** |
| `h10_volume` (pre-fix) | 40% | 0% | **Invalid** (no seeding) |
| `h10_volume` (pre-fix) | 60% | 0% | **Invalid** (no seeding) |
| Band 60% post-fix | — | Not rerun | **Gap** |

At 40% repeat (post-fix): cache reduces LLM calls and latency. Cost delta smaller because template writer also reduces B cost on misses.

### 2.2 Calibrated belief thresholds?

From `h10_slices_pilot_60` (`benchmark/belief_calibration.py`):

| Knob | Value | Sample size |
|------|-------|-------------|
| `confidence_stop` | **1.0** | 51 cache scores |
| `groundedness_floor` | **0.5** | 21 grounding scores |
| `memory_confidence_gate` | **0.5** | (same) |

Notes: `cache_score separation (mean hit − miss): 0.7524`.  
**Caveat:** `confidence_stop=1.0` reflects exact-repeat hits scoring 1.0 — conservative for production; needs more paraphrase-hit samples before enabling knobs.

### 2.3 Net A/B with CIs — who wins?

**Canonical run (`h10_slices_pilot_60`, band 40%):**

| Metric | A (LangGraph) | B (ChorusGraph) | Winner |
|--------|---------------|-----------------|--------|
| Full workload accuracy | 35.0% [22.4%, 47.6%] | **82.8%** [75.2%, 90.4%] | B |
| FX-only accuracy | 26.7% [12.3%, 41.0%] | **82.2%** [73.7%, 90.7%] | B |
| Latency P50 | 2291 ms | **523 ms** | B |
| Cost/task | $0.000160 | **$0.000104** | B |
| LLM calls/task | 2.0 | **~1.1** | B |

**Do not quote “A = 35%” without slice context.** A is depressed on memory tasks (no Cortex) and struggles on some FX tool-grounding vs canonical rubric — **that is a real baseline number**, not a strawman.

**Cross-session memory (n=5, empty history):** A **40%** [3%, 77%] vs B **100%** — B-only long-term recall demonstrated; CI wide on A due to n.

### 2.4 Residual asymmetries a skeptic would challenge?

1. **B-only:** semantic cache, Cortex, template writer, compound fast path (`FAIRNESS_H9.md` §3).  
2. **Full-workload accuracy** mixes FX and memory — use **slices** (now in `BENCHMARK_RESULTS.md`).  
3. **LangGraph FX accuracy ~27%** on FX-only slice — investigate whether A tool-calling or rubric strictness is the limiter; do not hide it.  
4. **Thresholds 0.88/0.95** are measured defaults, not per-slug CACHEABLE frontier (n ≪ MIN_HITS=300).  
5. **Local Gemini**, not Azure — environment disclosure in `run_meta.json`.  
6. **Multi-phrase cache seeding** is a B product behavior (seeds all canonical phrasings after FX tool) — improves paraphrase hits; document as framework feature.

### 2.5 Is MVP done?

**Director: YES** — fixes worked; FX effective; proceed with pilots/consultant.  
**Optional later:** 300-task volume (tighter CIs), git tag, LangGraph FX triage — not MVP blockers.

---

## 3. Per-band results tables (with CIs)

### 3.1 Canonical post-fix — `h10_slices_pilot_60` (band 40%, n=60)

**Headline (full workload):**

| Metric | A (95% CI) | B (95% CI) |
|--------|------------|------------|
| latency_ms_p50 | 2291 [2226, 2587] | 523 [16, 2629] |
| cost_per_task_usd | 0.000160 [0.000154, 0.000166] | 0.000104 [0.000075, 0.000144] |
| accuracy_rate | 0.350 [0.224, 0.476] | 0.828 [0.752, 0.904] |
| b_cache_hit_rate | — | 0.414 [0.286, 0.542] |

**Sliced accuracy (mandatory for external claims):**

| Slice | n (A/B) | A accuracy | B accuracy | B cache hit-rate |
|-------|---------|------------|------------|------------------|
| Full workload | 60/60 | 0.35 [0.22, 0.48] | 0.83 [0.75, 0.90] | 0.41 [0.29, 0.54] |
| FX + compound (no memory) | 49/49 | 0.27 [0.13, 0.40] | 0.80 [0.71, 0.89] | 0.49 [0.35, 0.63] |
| FX only | 45/45 | 0.27 [0.12, 0.41] | 0.82 [0.74, 0.91] | 0.49 [0.35, 0.63] |
| Cross-session memory | 5/5 | 0.40 [0.03, 0.77] | 1.00 [1.00, 1.00] | — |
| All memory tasks | 11/11 | 0.73 [0.55, 0.90] | 1.00 [1.00, 1.00] | — |

**Cache by variant (B, FX):**

| Variant | Hit rate |
|---------|----------|
| exact_repeat | **100%** (16/16) |
| paraphrase | **67%** (6/9) |

**Paraphrase forensics (verify=0.95):** misses had verify≈0, coarse≈0.34 — failures are below coarse gate, not borderline verify.

### 3.2 Volume pre-fix — `h10_volume` (INVALID for cache; valid for A/B at scale)

**Band 40% (n=1000):**

| Metric | A | B |
|--------|---|---|
| accuracy_rate | 0.737 [0.711, 0.763] | 0.843 [0.822, 0.864] |
| latency_ms_p50 | 3347 [3229, 3469] | 2612 [2591, 2625] |
| b_cache_hit_rate | — | **0.000** [0.0, 0.004] ⚠️ pre-fix |

**Band 60% (n=1000):**

| Metric | A | B |
|--------|---|---|
| accuracy_rate | 0.755 [0.729, 0.781] | 0.866 [0.846, 0.886] |
| latency_ms_p50 | 3355 [3247, 3471] | 2555 [2543, 2571] |
| b_cache_hit_rate | — | **0.000** [0.0, 0.004] ⚠️ pre-fix |

Use this run for **“B wins on accuracy/latency at 1000 tasks”** only. **Do not** use for cache claims.

---

## 4. What we fixed (chronological — consultant technical brief)

### 4.1 H10 §2.1–2.2 (defects)

- Compound intent → `compound_tool` / `compound_interest` before FX ReAct.
- `benchmark/rubric.py` — grounded FX pair + compound FV; no “any decimal passes.”

### 4.2 Cache was 0% — root cause and fix

| Issue | Fix |
|-------|-----|
| ReAct path never called `seed_tool_cache` after `fetch_exchange_rate` | `seed_fx_cache_from_tool_calls()` in `pattern_nodes.py` state_mapper |
| `cache_score` dropped by LangGraph | Added `cache_score`, `cache_coarse_score`, `cache_verify_score` to `PatternState` |
| Paraphrase misses at verify 0.95 | **Multi-phrase seeding** — seed all `CANONICAL_QUERIES` phrases for intent after tool (not threshold hand-tuning) |

### 4.3 Memory (H10 §2.3, §2.7)

- Workload: `memory_seed` session N → `memory_recall_cross` session N+1 (`memory_every_n_sessions=2`).
- Removed demo `"risk tolerance"` fallback in `cortex_service.py`.
- B runner: per-session cortex dirs via `memory_cortex_group`; `wait_for_digest` on seed and before cross-session recall.
- A runner: empty history on cross-session recall (fair).

### 4.4 Reporting (Director request)

- `benchmark/analyze.py` — `compare_ab_slices`, `paraphrase_cache_forensics`, `format_slice_table`.
- `benchmark/rebuild_analysis.py`, `benchmark/generate_results_doc.py`.
- `benchmark/archive_results.py` → `tests/fixtures/benchmark_results/`.

---

## 5. Acceptance criteria checklist (handoffH10 §4)

| Criterion | Met? | Evidence |
|-----------|------|----------|
| Compound routes correctly | ✅ | `tests/test_compound_rubric.py`, compound path in `patterns_graph.py` |
| Grounded rubric only | ✅ | `benchmark/rubric.py`, `tests/test_benchmark.py` |
| Cache workload all bands ≥1000 + CIs | ⚠️ | 1000×40+60 pre-fix only; **no post-fix 1000**; band 20 not in h10_volume |
| Cache hit-rate + cost/latency per band | ✅ pilot / ⚠️ volume | §3 tables |
| Belief thresholds calibrated | ✅ pilot | §2.2; small n |
| Fairness disclosed + BENCHMARK_RESULTS | ✅ | `FAIRNESS_H9.md`, `docs/BENCHMARK_RESULTS.md` |
| Tagged release | ❌ | `pyproject.toml` still **0.9.1**; no git tag pushed |
| No mocks in canonical run | ✅ | Real Gemini, real Frankfurter |
| No winner without CIs | ✅ | All tables include Wilson/bootstrap CIs |

---

## 6. Honest wins and losses

### Wins (B / ChorusGraph) — **Director: primary story**

- **Overall fixes validated** — see §1 before/after table; 0% → 41% cache is the proof the wiring hole is closed.
- **FX good and effective** — ~82% accuracy, ~49% cache on FX, 100% exact-repeat, 67% paraphrase (pilot).
- **Cache in the loop** — skips ReAct on hit; material latency/cost savings.
- **Cross-session memory** — 5/5 vs 2/5 on recall with empty chat history (pilot n).
- **Belief signals** — calibration pipeline works; not production-enabled yet.

### Losses / gaps / risks — **optional follow-up, not fix failures**

- **LangGraph FX accuracy ~27%** on FX-only — real, needs consultant triage (tool routing? rubric? model behavior?).
- **h10_volume cache 0%** — historical artifact; must stay labeled invalid for cache.
- **Architect volume spec incomplete** — no post-fix 1000×3, no Azure run, no band 20 post-fix.
- **CACHEABLE slug verdict** — INSUFFICIENT DATA (n_would_serve ≪ 300).
- **Enterprise track (E1–E9)** — not started; no load test, no CI fixtures tier.
- **Production belief knobs** — calibrated only; not enabled.

---

## 7. File tree (consultant — key paths)

```
benchmark/
├── analyze.py              # CIs + slice_compare_ab + paraphrase forensics
├── archive_results.py      # → tests/fixtures/benchmark_results/
├── container_a/runner.py   # LangGraph baseline
├── container_b/runner.py   # ChorusGraph + cache + cortex groups
├── FAIRNESS_H9.md
├── generate_results_doc.py
├── rebuild_analysis.py
├── rubric.py
├── run_volume.py
├── workload.py             # memory_seed, memory_recall_cross, CANONICAL_QUERIES
└── results/
    ├── h10_slices_pilot_60/    ★ CANONICAL post-fix
    ├── h10_volume/             ⚠ cache invalid (pre-fix)
    └── ...

chorusgraph/
├── examples/finance_agent/
│   ├── nodes.py            # cache_gate, seed_fx_cache_from_tool_calls
│   ├── pattern_nodes.py    # ReAct + cache seed mapper
│   └── patterns_graph.py   # PatternState includes cache_score fields
└── memory/cortex_service.py  # recall fix (no demo fallback)

docs/BENCHMARK_RESULTS.md
tests/fixtures/benchmark_results/MANIFEST.json
handoffs/handoffH10.md          # architect spec (partially superseded)
handoffs/handoffbackH10.md      # this file
```

---

## 8. How to run (consultant)

### API key

```powershell
cd c:\code\ChorusGraph
# GEMINI_API_KEY in .env (gitignored)
python scripts/verify_gemini_keys.py
```

### Rebuild analysis from JSONL (no API cost)

```powershell
python -m benchmark.rebuild_analysis benchmark/results/h10_slices_pilot_60 40 --tasks 60 --seed 82
python -m benchmark.generate_results_doc benchmark/results/h10_slices_pilot_60/aggregate_analysis.json docs/BENCHMARK_RESULTS.md
```

### New validation run (recommended: 300 tasks band 60)

```powershell
python -m benchmark.run_volume --tasks 300 --bands 60 --output-dir benchmark/results/h10_postfix_band60_300 --no-resume
python -m benchmark.archive_results --run h10_postfix_band60_300 --copy-jsonl
```

### Tests (no Gemini for most)

```powershell
python -m pytest tests/test_benchmark.py tests/test_finance_agent.py tests/test_compound_rubric.py -q -k "not test_dry_run"
```

---

## 9. Recommended next steps for consultant

| Priority | Action | Why |
|----------|--------|-----|
| **P0** | Read `MANIFEST.json` + §0–§1 of this doc | Director closed MVP; know valid vs invalid runs |
| **P1** | **External claim language** — FX + cache pilot stats with slices | Director-approved story; avoid raw “A=35%” |
| **P2** | Optional: **300 tasks band 60** post-fix | Tighter CIs only — not required for MVP |
| **P2** | Optional: Git tag **v0.9.1** (Director permission for push) | Release marker |
| **P3** | Optional: Triage **LangGraph FX ~27%** | Skeptic question; not a ChorusGraph fix failure |
| **P3** | Enterprise E1 (CI + fixture tests) | Separate track — `docs/ENTERPRISE_READINESS.md` |

### Out of scope for consultant unless Director expands

- Azure migration of Python benchmark (ACI containers run `chorus-protocol`, not this harness).
- Lowering verify threshold without shadow calibration (anti-rigging).
- Giving LangGraph Cortex “to be fair” — fairness doc already frames as product delta.

---

## 10. Decisions (Director)

| Decision | Resolution |
|----------|------------|
| **Did overall fixes work?** | **YES** — Director sign-off 2026-07-02 |
| **Is FX (ChorusGraph) good and effective?** | **YES** — ~82% FX-only accuracy, ~49% cache, strong latency/cost (pilot n=60) |
| **MVP closed for pilots?** | **YES** — use `h10_slices_pilot_60` + sliced `BENCHMARK_RESULTS.md` |
| **External claim tier** | **Pilot OK** — 300/1000 post-fix volume optional, not required |
| **Release tag** | **Pending** — v0.9.1 when Director approves push |
| **LangGraph FX ~27%** | **Accept as real baseline** for now; optional consultant triage |
| **Consultant mandate** | Onboard from this doc; polish claims/volume only if Director asks |

---

## 11. Version / git

- `pyproject.toml`: **0.9.1**
- `run_meta.json` code_version: **0.9.2** (benchmark harness fixes list)
- **No git tag created** in this pass (Director: no push without permission).

---

*Handoff H10 return · Director: Amin · **MVP closed — fixes worked · FX effective · cache validated (pilot)** · consultant handoff ready · optional: tag + volume rerun.*
