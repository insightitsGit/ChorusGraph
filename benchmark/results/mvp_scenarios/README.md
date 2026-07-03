# MVP Scenario Benchmark Archive

Canonical store for the **8-scenario matrix** (FL1/FC1/FL2/FC2/HL1/HC1/HL2/HC2) LangGraph vs ChorusGraph comparisons.

## Latest canonical run

| Field | Value |
|-------|-------|
| **Run ID** | `20260703_042206` |
| **Label** | MVP 8-scenario pilot (post-HC1 fix) |
| **Tasks** | 40 per scenario, seed 42, repeat band 40% |
| **Platform** | Azure Container Instances (4 CPU / 8 GB) |
| **Date (UTC)** | 2026-07-03 |

**Quick paths**

- Summary (JSON): [`20260703_042206/summary.json`](20260703_042206/summary.json)
- Comparison report: [`20260703_042206/COMPARISON_REPORT.md`](20260703_042206/COMPARISON_REPORT.md)
- Full metadata + per-task rows: [`20260703_042206/run_meta.json`](20260703_042206/run_meta.json)
- Comparison stats only: [`20260703_042206/comparison.json`](20260703_042206/comparison.json)
- Pointer file: [`latest.json`](latest.json)

**Blob backup:** `stinsightitsprod01/benchmark-results/mvp_scenarios/20260703_042206/`

## Headline results (run `20260703_042206`)

| Group | Winner | Task success (L → C) | Mean latency (L → C) | Cache hit (C) |
|-------|--------|----------------------|------------------------|---------------|
| Finance single (FL1 vs FC1) | **ChorusGraph** | 75% → 85% | 5194 → 1386 ms | 48% |
| Finance multi (FL2 vs FC2) | **ChorusGraph** | 70% → 88% | 3245 → 1057 ms | 48% |
| Healthcare single (HL1 vs HC1) | **Tie** | 72.5% → 72.5% | 6798 → 6742 ms | 0% |
| Healthcare multi (HL2 vs HC2) | **ChorusGraph** | 58% → 45%* | 10145 → 3196 ms | 63% |

\*HC2 trades slightly lower success for large latency/cache gains on this workload.

## Run history

| Run ID | Tasks | Notes | Path |
|--------|-------|-------|------|
| **20260703_042206** | 40 | **Canonical** — HC1 engine fix validated | [`20260703_042206/`](20260703_042206/) |
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
