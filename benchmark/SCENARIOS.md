# MVP Scenario Matrix

| ID | Domain | Mode | Framework | Path |
|---|---|---|---|---|
| **FL1** | Finance | Single-agent | LangGraph | `benchmark/fl1/` |
| **FC1** | Finance | Single-agent | ChorusGraph | `benchmark/fc1/` |
| **FL2** | Finance | Multi-agent | LangGraph | `benchmark/fl2/` |
| **FC2** | Finance | Multi-agent | ChorusGraph | `benchmark/fc2/` |
| **HL1** | Healthcare | Single-agent | LangGraph | `benchmark/hl1/` |
| **HC1** | Healthcare | Single-agent | ChorusGraph | `benchmark/hc1/` |
| **HL2** | Healthcare | Multi-agent | LangGraph | `benchmark/hl2/` |
| **HC2** | Healthcare | Multi-agent | ChorusGraph | `benchmark/hc2/` |

Legacy containers A–F were renamed to this matrix (old dirs removed).

## Run all scenarios

```powershell
# Requires GEMINI_API_KEY in .env
python -m benchmark.run_scenarios --tasks 12 --scenarios all
```

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
| **Cache proof** | LLM calls on cache hit | Should be **0** |
| **Multi-agent** | Embed count per task | Lower |
| **Healthcare** | Abstain rate | Context-dependent |

**Paired deltas** (same task/case): cost Δ, latency Δ, LLM calls Δ, success Δ — ChorusGraph minus LangGraph.

**Winner rule:** non-overlapping 95% CIs → clear winner; overlapping CIs → marginal (point estimate).

**By variant slice:** novel / exact_repeat / paraphrase breakdowns in `comparison.json`.

## Route Ledger (ChorusGraph scenarios)

FC1, FC2, HC1, HC2 emit native Route Ledger steps via `wrap()` — node, edge, `rule_chain`, cache_hit, duration_ms.
