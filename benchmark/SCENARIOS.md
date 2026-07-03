# MVP Scenario Matrix

> **Terminology:** **ChorusGraph** (FC*, HC*) = native `chorusgraph.core.Graph` + full Prism stack — **never LangGraph**. **LangGraph** (FL*, HL*) = baseline comparison only. Policy: [`docs/TERMINOLOGY.md`](../docs/TERMINOLOGY.md) · enforced by `tests/test_fc_hc_no_langgraph.py`.

| ID | Domain | Mode | Framework | Path |
|---|---|---|---|---|
| **FL1** | Finance | Single-agent | LangGraph baseline | `benchmark/fl1/` |
| **FC1** | Finance | Single-agent | **ChorusGraph native** | `benchmark/fc1/` |
| **FL2** | Finance | Multi-agent | LangGraph baseline | `benchmark/fl2/` |
| **FC2** | Finance | Multi-agent | **ChorusGraph native** | `benchmark/fc2/` |
| **HL1** | Healthcare | Single-agent | LangGraph baseline | `benchmark/hl1/` |
| **HC1** | Healthcare | Single-agent | **ChorusGraph native** | `benchmark/hc1/` |
| **HL2** | Healthcare | Multi-agent | LangGraph baseline | `benchmark/hl2/` |
| **HC2** | Healthcare | Multi-agent | **ChorusGraph native** | `benchmark/hc2/` |

Legacy containers A–F were renamed to this matrix (old dirs removed).

## Run all scenarios

```powershell
# Requires GEMINI_API_KEY in .env
python -m benchmark.run_scenarios --tasks 12 --scenarios all

# Workload tiers (same 40% repeat band; task count per scenario)
python -m benchmark.run_scenarios --tier light --scenarios all   # 40 tasks — smoke / CI
python -m benchmark.run_scenarios --tier mid --scenarios all     # 100 tasks — regression
python -m benchmark.run_scenarios --tier heavy --scenarios all  # 300 tasks — scale
```

Azure: pass `-Tier light` to `benchmark/azure/deploy_and_run.ps1` or set `BENCHMARK_TIER=light` on the container (`--tier` overrides `--tasks` when set).

`run_meta.json` records `tier`, `cache_profiles` (thresholds + profile registry), and per-scenario summaries.

## Honest cold-path run (0% cache)

Disable semantic cache on all ChorusGraph scenarios so repeat/paraphrase tasks still run the full LLM pipeline — surfaces real failure modes (e.g. HC2 writer/safety gaps) without cache masking them:

```powershell
python -m benchmark.run_scenarios --scenarios all --tasks 40 --seed 42 --no-cache
```

Azure: set `BENCHMARK_NO_CACHE=1` on the container.

`COMPARISON_REPORT.md` leads with **Task success** and **LLM calls / task**; `run_meta.json` includes `"cache_enabled": false`.

## Run pairs

```powershell
# Finance single-agent A/B
python -m benchmark.run_scenarios --scenarios FL1,FC1 --tasks 20

# Healthcare multi-agent A/B
python -m benchmark.run_scenarios --scenarios HL2,HC2 --tasks 18

# Presets: finance | healthcare | single | multi
python -m benchmark.run_scenarios --scenarios single --tasks 12
```

Results land in `benchmark/results/mvp_scenarios/` as `{fl1,fc1,...}.jsonl`, `run_meta.json`, **`comparison.json`**, and **`COMPARISON_REPORT.md`**.

**Archived runs:** see [`benchmark/results/mvp_scenarios/README.md`](results/mvp_scenarios/README.md) — latest canonical run is `20260703_042206` (40 tasks, Azure ACI).

Sample corpora: see [`benchmark/data/SAMPLE_DATA.md`](data/SAMPLE_DATA.md) (20 healthcare cases, 11 finance intents, 5 memory profiles).

## Group comparisons (LangGraph vs ChorusGraph)

Each pair is compared on the **same task IDs** (paired analysis):

| Group | LangGraph | ChorusGraph |
|-------|-----------|-------------|
| Finance single | FL1 | FC1 |
| Finance multi | FL2 | FC2 |
| Healthcare single | HL1 | HC1 |
| Healthcare multi | HL2 | HC2 |

### Metrics tracked (with 95% confidence intervals)

| Category | Metric | Better when |
|----------|--------|-------------|
| **Speed** | Latency p50, p95, mean | Lower |
| **Cost** | USD per task | Lower |
| **Quality** | Task success rate | Higher |
| **Efficiency** | LLM calls per task | Lower |
| **Tokens** | Tokens in/out per task | Lower |
| **Tools** | Tool calls per task | Lower |
| **Reliability** | Error rate | Lower |
| **Cache (Chorus)** | Cache hit rate | Higher |
| **Cache proof** | LLM calls on cache hit | Finance: **0** on whole-answer hit; Healthcare (archetype C): facts prefilled, judgment hops still run |

**Paired deltas** (same task/case): cost Δ, latency Δ, LLM calls Δ, success Δ — ChorusGraph minus LangGraph.

**Winner rule:** non-overlapping 95% CIs → clear winner; overlapping CIs → marginal (point estimate).

**By variant slice:** novel / exact_repeat / paraphrase breakdowns in `comparison.json`.

## CacheProfile per scenario (H21)

Profiles from [`docs/CACHE_PROFILES.md`](../docs/CACHE_PROFILES.md) and `chorusgraph/sections/profiles.default.json`. Measure offline: `python -m benchmark.run_profiler`.

| Scenario | Category slugs | keying | ttl | scope | risk |
|----------|----------------|--------|-----|-------|------|
| **FC1 / FC2** | `fx_rates` | semantic | 1h | global | low |
| **FC1 / FC2** | `user_profile` | semantic | none | user | low |
| **FC1 / FC2** | `compound_savings` | semantic | none | global | low |
| **HC1 / HC2** | `clinical_retrieval` / `clinical_guidelines` | semantic | 30d | **global** | low |
| **HC1 / HC2** | `clinical_judgment` | fingerprint | none | session | **high** |

HC1/HC2 use **facts-only cache** (retrieval, interactions) — writer judgment is never replayed. Quality-gated seeding blocks abstain/refusal chains from entering cache.

## Route Ledger (ChorusGraph scenarios)

FC1, FC2, HC1, HC2 emit native Route Ledger steps via `wrap()` — node, edge, `rule_chain`, cache_hit, duration_ms.
