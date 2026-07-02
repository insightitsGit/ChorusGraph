# ChorusGraph A/B Benchmark Results (H10)

**Methodology:** [`BENCHMARK.md`](BENCHMARK.md) · **Fairness:** [`benchmark/FAIRNESS_H9.md`](../benchmark/FAIRNESS_H9.md)

- **Run at:** 2026-07-02T16:22:19.603156+00:00
- **Environment:** local
- **Code:** 0.9.2 — react_cache_seed, pattern_state_cache_score, cross_session_memory, memory_every_n_sessions=2, canonical_phrase_cache_seed, slice_reporting, paraphrase_forensics
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
| 40% | latency_ms_p50 | 2291.0000 [2226.0, 2587.0] | 523.0000 [16.0, 2629.0] |
| 40% | cost_per_task_usd | 0.0002 [0.000154311875, 0.0001661276875] | 0.0001 [7.51152801724138e-05, 0.00014377525862068957] |
| 40% | accuracy_rate | 0.3500 [0.22362618841754867, 0.4763738115824513] | 0.8276 [0.7516153404224915, 0.903557073370612] |
| 40% | b_cache_hit_rate | — | 0.4138 [0.28557028860510836, 0.5420159182914434] |

## Per-band detail (with slices)

### Repeat band 40%

- Valid paired tasks: 58 (excludes 429 quota errors)
- Workload stats: `{'total': 60, 'sessions': 11, 'exact_repeat': 17, 'paraphrase': 10, 'novel': 22, 'memory_seed': 6, 'memory_recall': 0, 'memory_recall_cross': 5}`
- **Full workload** task success A: 0.3500 [0.2236, 0.4764]
- **Full workload** task success B: 0.8276 [0.7516, 0.9036]
- B cache hit-rate (Wilson 95% CI): 0.4138 [0.2856, 0.5420]
- **Cost:** B lower — paired delta -0.0001 USD/task [-0.0001, -0.0000] (B−A, 95% bootstrap CI)
- **Latency:** B lower — paired delta -967.3793 ms [-1421.6871, -494.3440] (B−A, 95% bootstrap CI)
- fx_rates slug: n_serve=22, FP upper95=0.4343995317522171, verdict=INSUFFICIENT DATA

#### Sliced accuracy (do not quote full-workload A alone)

| Slice | n (A/B) | A accuracy (95% CI) | B accuracy (95% CI) | B cache hit-rate |
|-------|---------|---------------------|---------------------|------------------|
| Full workload (FX + compound + memory) | 60/60 | 0.3500 [0.2236, 0.4764] | 0.8276 [0.7516, 0.9036] | 0.4138 [0.2856, 0.5420] |
| FX + compound only (excludes memory tasks) | 49/49 | 0.2653 [0.1280, 0.4026] | 0.7959 [0.7067, 0.8852] | 0.4898 [0.3543, 0.6253] |
| FX rate tasks only | 45/45 | 0.2667 [0.1229, 0.4104] | 0.8222 [0.7374, 0.9071] | 0.4889 [0.3478, 0.6300] |
| Cross-session memory recall (empty chat history) | 5/5 | 0.4000 [0.0307, 0.7693] | 1.0000 [1.0000, 1.0000] | — |
| All memory tasks | 11/11 | 0.7273 [0.5520, 0.9025] | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.2991] |

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
