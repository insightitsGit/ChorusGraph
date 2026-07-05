# MVP Scenario Benchmark Archive

Canonical store for the **8-scenario matrix** (FL1/FC1/FL2/FC2/HL1/HC1/HL2/HC2) LangGraph vs ChorusGraph comparisons.

## Latest canonical run

| Field | Value |
|-------|-------|
| **Run ID** | `20260704_212111` |
| **Label** | MVP 8-scenario matrix (post-HC2 Bug-1 fix + chromadb Azure image) |
| **Tasks** | 40 per scenario, seed 42, repeat band 40% |
| **Platform** | Azure Container Instances (4 CPU / 8 GB) |
| **Git commit** | `f43f532` |
| **Date (UTC)** | 2026-07-04 |

**Quick paths**

- Summary (JSON): [`20260704_212111/summary.json`](20260704_212111/summary.json)
- Comparison report: [`20260704_212111/COMPARISON_REPORT.md`](20260704_212111/COMPARISON_REPORT.md)
- Full metadata + per-task rows: [`20260704_212111/run_meta.json`](20260704_212111/run_meta.json)
- Comparison stats only: [`20260704_212111/comparison.json`](20260704_212111/comparison.json)
- Pointer file: [`latest.json`](latest.json)

**Blob backup:** `stinsightitsprod01/benchmark-results/mvp_scenarios/20260704_212111/`

## Headline results (run `20260704_212111`)

| Group | Winner | Task success (L → C) | Mean latency (L → C) | Cache hit (C) |
|-------|--------|----------------------|------------------------|---------------|
| Finance single (FL1 vs FC1) | **ChorusGraph** | 87.5% → **100%** | 5079 → 1548 ms | 47.5% |
| Finance multi (FL2 vs FC2) | **ChorusGraph** | 75% → **87.5%** | 3265 → 1359 ms | 40% |
| Healthcare single (HL1 vs HC1) | **Tie** | 72.5% → 72.5% | 7700 → 5048 ms | 42.5% |
| Healthcare multi (HL2 vs HC2) | **ChorusGraph** | 57.5% → **87.5%** | 11150 → 11546 ms | 25% |

HC2 wins on **success (+30 pts)**, **LLM calls**, and **abstain rate** vs HL2; latency is essentially a tie. Lower HC2 cache hit (25% vs pre-fix 62.5%) is intentional — quality-gated facts-only hits (archetype C).

## Run history

| Run ID | Tasks | Notes | Path |
|--------|-------|-------|------|
| **20260704_212111** | 40 | **Canonical** — HC2 Bug-1 fix + chromadb Azure image | [`20260704_212111/`](20260704_212111/) |
| 20260703_042206 | 40 | Pre-HC2-fix; HC2 45% success (invalid for HC2 claims) | [`20260703_042206/`](20260703_042206/) |
| azure_20260704_204940 | 40 | Broken — missing chromadb in image | `benchmark/results/azure_20260704_204940/` |
| 20260703_034124 | 40 | Pre-HC1 fix; HC1 0% success (invalid) | `benchmark/results/azure_20260703_034124/` |
| 20260703_011048 | 12 | Smoke run | `benchmark/results/azure_20260703_011048/` |

## Reproduce

```powershell
# Local
python -m benchmark.run_scenarios --tasks 40 --seed 42 --repeat-band 40 --scenarios all

# Azure ACI
.\benchmark\azure\deploy_and_run.ps1 -Tasks 40 -Seed 42 -RepeatBand 40 -Wait
```

See [`benchmark/SCENARIOS.md`](../../SCENARIOS.md) for scenario definitions.
