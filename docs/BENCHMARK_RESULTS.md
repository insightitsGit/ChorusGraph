# ChorusGraph A/B Benchmark Results (H9)

**Methodology:** [`BENCHMARK.md`](BENCHMARK.md) · **Fairness:** [`benchmark/FAIRNESS_H9.md`](../benchmark/FAIRNESS_H9.md)

- **Run at:** 2026-07-02T01:47:59.136422+00:00
- **Environment:** local *(Azure rerun required — see Quota)*
- **Tasks per band (target):** 1000
- **Repeat bands:** 20%, 40%, 60%

> **No overall winner declared.** All metrics include 95% confidence intervals where valid.

## Quota / run status

Gemini daily quota (`gemini-2.5-flash`, 10k req/day) was exhausted mid-run:
- **Band 20%:** ~599 valid paired tasks (of 1000) — results below use **valid rows only**.
- **Bands 40% / 60%:** 100% quota-blocked (429) — **re-run on Azure with fresh API key/billing**.

## Fairness confirmation (pre-run)

- Container B uses **LLM ReAct/AgentNode** path (not regex researcher).
- Accuracy rubric scores **answer content** identically for A and B.

## Results with confidence intervals

| Band | Metric | A (95% CI) | B (95% CI) |
|------|--------|------------|------------|
| 20% | latency_ms_p50 | 2858.0000 [2729.0, 3031.0] | 5383.5000 [5229.0, 5498.0] |
| 20% | cost_per_task_usd | 0.0002 [0.0002288686665275459, 0.00023879109766277126] | 0.0004 [0.00039634459239130433, 0.00041350183946488295] |
| 20% | accuracy_rate | 0.9115 [0.8913202156531734, 0.9317181816757081] | 0.9047 [0.8836627790667511, 0.9257017694282321] |
| 20% | b_cache_hit_rate | — | 0.0000 [0.0, 0.006382841800598862] |

## Per-band detail

### Repeat band 20%

- Valid paired tasks: 598 (excludes 429 quota errors)
- Workload stats: `{'total': 1000, 'sessions': 200, 'exact_repeat': 89, 'paraphrase': 78, 'novel': 833}`
- B cache hit-rate (Wilson 95% CI): 0.0000 [0.0000, 0.0064]
- Paired cost delta (B−A): 0.0002 [0.0002, 0.0002]
- Paired latency delta (B−A ms): 3283.9799 [3016.5944, 3546.5952]
- fx_rates slug: n_serve=0, FP upper95=1.0, verdict=INSUFFICIENT DATA

### Repeat band 40% — **QUOTA BLOCKED**

- Valid tasks: 0 / 1000
- Re-run required on Azure.

### Repeat band 60% — **QUOTA BLOCKED**

- Valid tasks: 0 / 1000
- Re-run required on Azure.

## Belief-knob calibration (derived, not enabled in production)

- `confidence_stop`: None
- `groundedness_floor`: None
- `memory_confidence_gate`: None
- Notes: ['groundedness_floor unavailable — no Cortex recall in benchmark tasks']

## Honest wins and losses (band 20% — valid tasks only)

**Latency:** B is slower — paired delta +1963 ms [+1783, +2150] (B−A, 95% bootstrap CI).
**Cost:** B is more expensive — paired delta +$0.00010/task [+$0.00009, +$0.00011].
**Accuracy:** Tied within CI — A 54.6% [51.5%, 57.7%] vs B 54.1% [51.0%, 57.2%].
**Cache:** No semantic cache hits at 20% repeat (hit-rate 0% [0%, 0.4%]); fx_rates slug INSUFFICIENT DATA (n_serve=0).

**Surprising ChorusGraph disadvantage:** With fair LLM ReAct on both sides, B uses ~2.5 LLM calls/task vs A ~1.4,
and is ~2× slower at P50 — graph depth (cache_gate + react + writer + validator) without cache benefit.

Bands 40%/60% sensitivity **not yet measured** (quota). Hypothesis: cache benefit may appear at higher repeat rates.
