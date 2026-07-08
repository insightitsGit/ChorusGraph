# MVP Scenario Benchmark Archive

Canonical store for the **8-scenario matrix** (FL1/FC1/FL2/FC2/HL1/HC1/HL2/HC2) LangGraph vs ChorusGraph comparisons.

## Latest canonical run

| Field | Value |
|-------|-------|
| **Run ID** | `mid_20260708_111539` |
| **Label** | MVP 8-scenario matrix — post-fix prompt + fair comparison (100 tasks/scenario) |
| **Tier** | mid (100 tasks per scenario, seed 42) |
| **Platform** | Azure Container Instances (4 CPU / 8 GB) |
| **Benchmark fix commit** | `eeba2ad` (no `chorusgraph/` library change) |
| **Date (UTC)** | 2026-07-08 |

**Quick paths**

- Comparison report: [`../azure_mid_20260708_111539/mvp_scenarios/mid_20260708_111539/COMPARISON_REPORT.md`](../azure_mid_20260708_111539/mvp_scenarios/mid_20260708_111539/COMPARISON_REPORT.md)
- Latency + LLM summary: [`../BENCHMARK_LATENCY_LLM_SUMMARY.md`](../BENCHMARK_LATENCY_LLM_SUMMARY.md)
- Full tarball + metadata: [`../azure_mid_20260708_111539/`](../azure_mid_20260708_111539/)
- Pointer file: [`latest.json`](latest.json)

**Smoke run (40 tasks):** `light_20260708_101409` — [`../azure_light_20260708_101409/`](../azure_light_20260708_101409/)

**Heavy run (300 tasks):** `heavy_20260708_124337` — in progress / see [`../azure_heavy_*`](../)

**Blob backup:** `stinsightitsprod01/benchmark-results/mvp_scenarios/mid_20260708_111539/`

## Headline results (run `mid_20260708_111539`)

| Group | Winner | Task success (L → C) | Mean latency (L → C) | LLM calls (L → C) | Cache hit (C) |
|-------|--------|----------------------|------------------------|-------------------|---------------|
| Finance single (FL1 vs FC1) | **ChorusGraph** | 87.0% → **98.0%** | 4760 → 1348 ms | 3.24 → 0.77 | 52% |
| Finance multi (FL2 vs FC2) | **ChorusGraph** | 87.0% → **94.0%** | 3269 → 1085 ms | 2.03 → 0.69 | 40% |
| Healthcare single (HL1 vs HC1) | **ChorusGraph** | 74.0% → **79.0%** | 7036 → 3990 ms | 3.00 → 1.56 | 60% |
| Healthcare multi (HL2 vs HC2) | **ChorusGraph** (success) | 59.0% → **85.0%** | 10296 → 10753 ms | 3.82 → 3.15 | 51% |

HC2 wins on **success (+26 pp)** and **fewer LLM calls** vs HL2; mean latency is a tie (multi-agent + Cortex embeds).

### What changed vs `20260704_212111`

Benchmark-only fixes (July 2026):

1. **FL2 prompt** — `annual_rate` → `annual_rate_pct` (matches tool schema; was hurting FC2 and hiding FL2 tool errors).
2. **Comparison script** — agent/tool errors stay in LangGraph success denominators (fair paired counts).

Do **not** quote pre-fix `mid_20260707_220458` FL2 vs FC2 success (inflated FL2, depressed FC2).

## Run history

| Run ID | Tasks | Notes | Path |
|--------|-------|-------|------|
| **mid_20260708_111539** | 100 | **Canonical** — post-fix regression | [`../azure_mid_20260708_111539/`](../azure_mid_20260708_111539/) |
| light_20260708_101409 | 40 | Smoke / CI | [`../azure_light_20260708_101409/`](../azure_light_20260708_101409/) |
| mid_20260707_220458 | 100 | Pre-fix (invalid FL2/FC2 comparison) | [`../azure_mid_20260707_220458/`](../azure_mid_20260707_220458/) |
| heavy_20260707_235024 | 300 | Pre-fix heavy baseline | [`../azure_heavy_20260707_235024/`](../azure_heavy_20260707_235024/) |
| 20260704_212111 | 40 | Prior canonical (pre comparison-fix) | [`20260704_212111/`](20260704_212111/) |
| 20260703_042206 | 40 | Pre-HC2-fix; HC2 45% (invalid for HC2 claims) | [`20260703_042206/`](20260703_042206/) |

## Reproduce

```powershell
# Local
python -m benchmark.run_scenarios --tier mid --seed 42 --scenarios all

# Azure ACI
.\benchmark\azure\deploy_and_run.ps1 -Tier mid -Wait -Cleanup
.\benchmark\azure\run_tier_benchmarks.ps1 -Tiers light_mid -Wait -Cleanup
```

See [`benchmark/SCENARIOS.md`](../../SCENARIOS.md) for scenario definitions.
