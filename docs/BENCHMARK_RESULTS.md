# ChorusGraph A/B Benchmark Results

## MVP matrix — Azure (canonical)

**Latest regression run:** `mid_20260708_111539` · 100 tasks/scenario · seed 42 · Azure ACI · real Gemini

| Pair | LangGraph success | ChorusGraph success | LLM calls (L → C) | Mean latency ms (L → C) |
|------|-------------------|---------------------|--------------------|-------------------------|
| FL1 / FC1 | 87.0% | **98.0%** | 3.24 → **0.77** | 4760 → **1348** |
| FL2 / FC2 | 87.0% | **94.0%** | 2.03 → **0.69** | 3269 → **1085** |
| HL1 / HC1 | 74.0% | **79.0%** | 3.00 → **1.56** | 7036 → **3990** |
| HL2 / HC2 | 59.0% | **85.0%** | 3.82 → **3.15** | 10296 → 10753 |

- Full report: [`benchmark/results/azure_mid_20260708_111539/mvp_scenarios/mid_20260708_111539/COMPARISON_REPORT.md`](../benchmark/results/azure_mid_20260708_111539/mvp_scenarios/mid_20260708_111539/COMPARISON_REPORT.md)
- Latency + LLM tables: [`benchmark/results/BENCHMARK_LATENCY_LLM_SUMMARY.md`](../benchmark/results/BENCHMARK_LATENCY_LLM_SUMMARY.md)
- Archive index: [`benchmark/results/mvp_scenarios/README.md`](../benchmark/results/mvp_scenarios/README.md)
- Methodology: [`BENCHMARK.md`](BENCHMARK.md) · fairness: [`benchmark/FAIRNESS_H9.md`](../benchmark/FAIRNESS_H9.md)

**Benchmark-only fixes (July 2026, commit `eeba2ad`):** FL2 prompt `annual_rate_pct`; fair LangGraph success denominator. **No library version bump required.**

Smoke (40 tasks): `light_20260708_101409`. Heavy (300 tasks): `heavy_20260708_124337` (scale tier).

---

## H10 FX workload (local, sliced metrics)

**Methodology:** [`BENCHMARK.md`](BENCHMARK.md) · **Fairness:** [`benchmark/FAIRNESS_H9.md`](../benchmark/FAIRNESS_H9.md)

- **Run at:** 2026-07-02T17:05:15.935964+00:00
- **Environment:** local
- **Code:** 0.9.3 — react_cache_seed, pattern_state_cache_score, cross_session_memory, memory_every_n_sessions=2, canonical_phrase_cache_seed, slice_reporting, paraphrase_forensics, container_a_fresh_turn_state, container_a_no_memory_saver, container_a_react_loop
- **Tasks per band (target):** 60
- **Repeat bands:** 40%

> **No overall winner declared.** Quote **sliced** metrics for fair comparisons.
> Full-workload A accuracy is depressed by cross-session memory tasks (no Cortex).

## Fairness (H10 §2.4)

- Container A = **competent LangGraph ReAct** baseline (not a strawman).
- Container B uses **LLM ReAct/AgentNode** for FX (not regex researcher).
- **Canonical rubric** scores grounded FX pair + compound FV (`benchmark/rubric.py`).
- B-only **template writer**, **compound fast path**, **cache**, **Cortex** disclosed in `FAIRNESS_H9.md` §3.

## Headline results (full workload)

| Band | Metric | A (95% CI) | B (95% CI) |
|------|--------|------------|------------|
| 40% | latency_ms_p50 | 4498.5000 [4193.925, 6770.0] | 575.0000 [16.5, 2648.0] |
| 40% | cost_per_task_usd | 0.0004 [0.00035028459051724136, 0.0004237840086206896] | 0.0001 [7.51148922413793e-05, 0.0001459491594827586] |
| 40% | accuracy_rate | 0.7931 [0.7087217362466297, 0.8774851603050945] | 0.8448 [0.7735000919439735, 0.9161550804698196] |
| 40% | b_cache_hit_rate | — | 0.4138 [0.28557028860510836, 0.5420159182914434] |

## Per-band detail (with slices)

### Repeat band 40%

- Valid paired tasks: 58 (excludes 429 quota errors)
- Workload stats: `{'total': 60, 'sessions': 11, 'exact_repeat': 17, 'paraphrase': 10, 'novel': 22, 'memory_seed': 6, 'memory_recall': 0, 'memory_recall_cross': 5}`
- **Full workload** task success A: 0.7931 [0.7087, 0.8775]
- **Full workload** task success B: 0.8448 [0.7735, 0.9162]
- B cache hit-rate (Wilson 95% CI): 0.4138 [0.2856, 0.5420]
- **Cost:** B lower — paired delta -0.0003 USD/task [-0.0003, -0.0002] (B−A, 95% bootstrap CI)
- **Latency:** B lower — paired delta -4629.4828 ms [-5395.0254, -3938.5116] (B−A, 95% bootstrap CI)
- fx_rates slug: n_serve=22, FP upper95=0.38516607437126543, verdict=INSUFFICIENT DATA

#### Sliced accuracy (do not quote full-workload A alone)

| Slice | n (A/B) | A accuracy (95% CI) | B accuracy (95% CI) | B cache hit-rate |
|-------|---------|---------------------|---------------------|------------------|
| Full workload (FX + compound + memory) | 60/60 | 0.7931 [0.7087, 0.8775] | 0.8448 [0.7735, 0.9162] | 0.4138 [0.2856, 0.5420] |
| FX + compound only (excludes memory tasks) | 49/49 | 0.8163 [0.7324, 0.9002] | 0.8163 [0.7324, 0.9002] | 0.4898 [0.3543, 0.6253] |
| FX rate tasks only | 45/45 | 0.8444 [0.7663, 0.9225] | 0.8444 [0.7663, 0.9225] | 0.4889 [0.3478, 0.6300] |
| Cross-session memory recall (empty chat history) | 5/5 | 0.0000 [0.0000, 0.5615] | 1.0000 [1.0000, 1.0000] | — |
| All memory tasks | 11/11 | 0.6667 [0.4539, 0.8794] | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.2991] |
| B cache — FX exact_repeat | —/16 | — | — | 1.0000 [1.0000, 1.0000] |
| B cache — FX paraphrase | —/9 | — | — | 0.6667 [0.4539, 0.8794] |

#### Paraphrase cache forensics (verify=0.95)

- FX paraphrase tasks: 9
- Hit / miss: 6 / 3
- Verify score on misses (mean / max): 0.0 / 0.0
- Coarse score on misses (mean): 0.34058308601379395

## Belief-knob calibration (derived, not enabled in production)

- `confidence_stop`: 1.0
- `groundedness_floor`: 0.5
- `memory_confidence_gate`: 0.5
- Notes: ['cache_score separation (mean hit - miss): 0.7524']

## Cache thesis

- **Exact repeat** hit-rate: see per-band `cache_exact_repeat` slice.
- **Paraphrase** hit-rate at verify=0.95: see forensics; multi-phrase seeding improves paraphrase hits without lowering threshold.
- Runs before cache-seed fix (`h10_volume`) are **invalid** for cache claims — see `tests/fixtures/benchmark_results/MANIFEST.json`.
