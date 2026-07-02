# Handoff H11 — Return · Engineer → Director (Amin)

**Date:** 2026-07-02  
**Status:** **H11 complete** — Container A baseline fixed; honest rerun done; held-out paraphrase measured.  
**Canonical A/B run (post-fix A):** `benchmark/results/h11_fixed_a_60`  
**Held-out paraphrase run:** `benchmark/results/h11_held_out_paraphrase_60`  
**Invalid for A/B claims:** `h10_slices_pilot_60` Container A metrics (broken baseline)

---

## 1. Executive summary

H11 proved the H10 “B 82% vs A 27%” FX gap was largely a **broken LangGraph baseline**, not ChorusGraph magic.

| Finding | Result |
|---------|--------|
| Root cause of A never calling tools | **(c) stale MemorySaver checkpoint** + **(a) model finish-without-action** + routing to writer |
| A FX `tool_calls ≥ 1` after fix | **45/45 (100%)** |
| Honest FX-only accuracy | **A 84.4%** vs **B 84.4%** — **tied** |
| B still wins | Latency **−4.6s/task**, cost **−$0.00028/task**, memory **100% vs 0%** cross-session |
| Held-out paraphrase cache (novel seed only) | **22%** (2/9) — real but modest; **67%** was inflated by multi-phrase seeding |
| B rewire required? | **No** for FX accuracy — B wins on product deltas fairly |

---

## 2. Root cause (H11 §6.1)

**Primary: (c) stale session state via LangGraph `MemorySaver`**

- `ContainerARunner` used `thread_id=session_id` with a checkpointer.
- `run_task()` reset `scratchpad` and `react_step` but **not** `react_done`, `tool_result`, or `pending_action`.
- Task N+1 inherited `react_done=True` → `route_after_react` jumped straight to **writer** without tools.

**Secondary: (a) model finish-without-tool + routing**

- Gemini often returned `finish=true` with `action=null` on FX queries.
- `route_after_react` sent no-action / not-done cases to **writer** instead of looping react.
- Removed scratchpad early-finish bug (old lines 87–88).

**Not (b):** `parse_react_json` was not the main failure mode.

---

## 3. What changed in Container A

| File | Change |
|------|--------|
| `benchmark/container_a/graph.py` | `fresh_turn_state()`; removed `MemorySaver`; react self-loop; block finish-without-tool on FX/compound |
| `benchmark/container_a/runner.py` | (unchanged API — benefits from graph fix) |
| `tests/test_container_a_graph.py` | Regression tests with stub Gemini |
| `benchmark/diagnose_container_a.py` | One-task routing diagnostic |
| `benchmark/shared/stub_gemini.py` | Shared offline stub |

**Nothing hobbled A or tuned B/rubric/thresholds.**

---

## 4. Honest rerun — `h11_fixed_a_60` (60 tasks, band 40%, seed 42)

### Headline (full workload, n=58 valid)

| Metric | A (LangGraph) | B (ChorusGraph) |
|--------|---------------|-----------------|
| Accuracy | **79.3%** [70.9%, 87.8%] | **84.5%** [77.4%, 91.6%] |
| Latency P50 | 4499 ms | **575 ms** |
| Cost/task | $0.000385 | **$0.000110** |
| LLM calls/task | 3.8 | **~1.1** |
| B cache hit-rate | — | **41.4%** [28.6%, 54.2%] |

### Sliced accuracy (mandatory for claims)

| Slice | A | B |
|-------|---|---|
| FX only (n=45) | **84.4%** [76.6%, 92.3%] | **84.4%** [76.6%, 92.3%] |
| FX + compound (n=49) | 81.6% | 81.6% |
| Cross-session memory (n=5) | 0% | **100%** |
| All memory (n=11) | 66.7% | **100%** |

### vs broken baseline (`h10_slices_pilot_60`)

| Metric | Pre-H11 A | Post-H11 A |
|--------|-----------|------------|
| FX tool_calls | **0/45** | **45/45** |
| FX-only accuracy | ~27% | **~84%** |
| Full workload accuracy | ~35% | **~79%** |

**Conclusion:** B’s FX accuracy advantage was a mirage. B’s **latency, cost, cache, and memory** advantages are real.

---

## 5. Held-out paraphrase (`h11_held_out_paraphrase_60`, `--cache-seed-mode novel-only`)

| Mode | Paraphrase FX cache hit-rate |
|------|------------------------------|
| Multi-phrase seed (H10 default) | **67%** (6/9) |
| Novel phrase only (held-out T) | **22%** (2/9) |

**Interpretation:** Semantic cache **does generalize** (not 0%), but H10’s 67% included **pre-loaded canonical phrasings**. Report both numbers; do not claim 67% as pure semantic generalization.

Miss forensics (held-out): many misses pass coarse (~0.56 mean) but fail verify=0.95 — borderline paraphrases need shadow calibration, not threshold lowering.

---

## 6. B rewire assessment (H11 §3.3)

| Gap | Action |
|-----|--------|
| B loses FX accuracy to fair A | **No gap** — tied at 84.4% |
| B loses latency/cost | **No fix needed** — B already wins |
| B loses cross-session memory | **Expected** — Cortex is a disclosed B feature |
| Compound paraphrase tasks mis-tagged `fx_rates` in workload | Known workload quirk; not addressed in H11 |

**No B code rewire was required** to win honestly on FX after fixing A.

---

## 7. Acceptance checklist (handoffH11 §5)

| Criterion | Met? |
|-----------|------|
| Root cause stated (a/b/c) | ✅ (c) + (a) |
| A `tool_calls ≥ 1` on FX | ✅ 45/45 |
| Fixed-A vs B rerun with CIs | ✅ `h11_fixed_a_60` |
| Pre-fix A numbers marked invalid | ✅ FAIRNESS_H9.md + this doc |
| B rewire for losses | ✅ N/A — no FX loss |
| Held-out paraphrase reported | ✅ 22% (2/9) |
| No hobbling / rubric gaming | ✅ |
| Prior tests green | ✅ |

---

## 8. How to run

```powershell
# Diagnose A routing (offline)
python -m benchmark.diagnose_container_a --stub

# Honest A/B rerun (same workload as H10 pilot)
python -m benchmark.run_volume --tasks 60 --bands 40 --output-dir benchmark/results/h11_fixed_a_60 --no-resume --seed 42 --run-label H11

# Held-out paraphrase (novel seed only)
python -m benchmark.run_volume --tasks 60 --bands 40 --output-dir benchmark/results/h11_held_out_paraphrase_60 --no-resume --seed 42 --run-label H11-held-out --cache-seed-mode novel-only

# Rebuild analysis / docs
python -m benchmark.rebuild_analysis benchmark/results/h11_fixed_a_60 40 --tasks 60 --seed 42
python -m benchmark.generate_results_doc benchmark/results/h11_fixed_a_60/aggregate_analysis.json docs/BENCHMARK_RESULTS.md

# Tests
python -m pytest tests/test_container_a_graph.py tests/test_benchmark.py -q -k "not test_dry_run"
```

---

## 9. Open questions answered

1. **Root cause?** Stale MemorySaver state (c) + early finish routing (a).  
2. **Fixed-A FX accuracy?** **84.4%** — ties B; honest delta is latency/cost/cache/memory, not FX rubric pass rate.  
3. **Held-out paraphrase real?** **Partially** — 22% hit vs 67% with multi-phrase seed.  
4. **Did fixing A flip any metric?** **Yes** — A accuracy +47pp FX; B still wins speed/cost/memory.

---

## 10. Recommended external claim language

- Use **`h11_fixed_a_60`** for A/B comparisons.  
- **Do not cite** `h10_slices_pilot_60` A accuracy.  
- FX: “Competent LangGraph ReAct baseline ties ChorusGraph on grounded FX accuracy; ChorusGraph wins on latency, cost, semantic cache, and cross-session memory.”  
- Cache: “41% hit-rate at 40% repeat; 100% exact-repeat; **22% held-out paraphrase** (novel seed only) vs **67%** with canonical phrase seeding.”

---

*Handoff H11 return · fair baseline restored · honest B wins on product merits · held-out cache measured.*
