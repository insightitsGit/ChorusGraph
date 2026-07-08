# Azure Container benchmark (ACI)

MVP scenario matrix (FL1–HC2) runs on **Azure Container Instances** — not VMs.

## Workload tiers

| Tier | Tasks / scenario | Total scenario-runs (×8) | Use |
|------|------------------|--------------------------|-----|
| `light` | 40 | 320 | Smoke / CI (previous canonical run) |
| **`mid`** | **100** | **800** | Regression |
| **`heavy`** | **300** | **2400** | Scale / threshold calibration |

Repeat band is **40%** for all tiers (same paraphrase/repeat mix).

## Quick start — 100 + 300 task benchmarks

```powershell
cd c:\code\ChorusGraph
# Requires: az CLI logged in, GEMINI_API_KEY in .env

# Run both mid (100) and heavy (300) sequentially — build once, auto-cleanup after each
.\benchmark\azure\run_tier_benchmarks.ps1 -Tiers both -Wait -Cleanup

# Or one tier at a time
.\benchmark\azure\deploy_and_run.ps1 -Tier mid -Wait -Cleanup
.\benchmark\azure\deploy_and_run.ps1 -Tier heavy -Wait -SkipBuild -Cleanup
```

| Flag | Meaning |
|------|---------|
| `-Tiers mid\|heavy\|both` | Which tier(s) to run (`run_tier_benchmarks.ps1`) |
| `-Tier mid\|heavy\|light` | Single deploy (`deploy_and_run.ps1`) |
| `-Wait` | Poll until done, download results locally |
| `-Cleanup` | Delete ACI after run (stops compute billing) |
| `-SkipBuild` | Reuse existing ACR image |

### Container sizing (auto per tier)

| Tier | vCPU | Memory | Container name |
|------|------|--------|----------------|
| light | 4 | 8 GB | `chorus-mvp-benchmark-light` |
| mid | 4 | 8 GB | `chorus-mvp-benchmark-mid` |
| heavy | 4 | 16 GB | `chorus-mvp-benchmark-heavy` |

Run IDs are prefixed with tier: `mid_20260708_120000`, `heavy_20260708_153000`.

## Single deploy (custom)

```powershell
.\benchmark\azure\deploy_and_run.ps1 -Wait
.\benchmark\azure\deploy_and_run.ps1 -Tier light -Wait -Cleanup
.\benchmark\azure\deploy_and_run.ps1 -Tasks 50 -Wait   # custom task count (no tier)
```

## What happens

1. **`az acr build`** — builds `chorusacrd7a6d0.azurecr.io/chorusgraph-mvp-benchmark:latest`
2. **`az container create`** — one-shot ACI in `chorus-rg-us` (`restart-policy Never`)
3. Container runs `python -m benchmark.run_scenarios --tier …` (or `--tasks …`)
4. Results upload to **`stinsightitsprod01`** blob: `benchmark-results/mvp_scenarios/{run_id}/`

## Manual commands

```powershell
# Follow logs while running
az container logs -g chorus-rg-us -n chorus-mvp-benchmark-mid --follow
az container logs -g chorus-rg-us -n chorus-mvp-benchmark-heavy --follow

# Download after run
.\benchmark\azure\fetch_results.ps1 -RunId mid_20260708_120000

# Stop billing immediately (if you didn't use -Cleanup)
az container delete -g chorus-rg-us -n chorus-mvp-benchmark-mid --yes
az container delete -g chorus-rg-us -n chorus-mvp-benchmark-heavy --yes
```

## Image contents

- `benchmark/azure/Dockerfile` — Python 3.11 + `[dev,gemini,cortex,benchmark-healthcare]`
- `benchmark/azure/entrypoint.sh` — runs scenarios, prints report, uploads tarball to blob

## Local fallback (no Azure)

```powershell
python -m benchmark.run_scenarios --tier mid --scenarios all    # 100 tasks
python -m benchmark.run_scenarios --tier heavy --scenarios all  # 300 tasks
```

## Cost note

ACI bills **only while the container is Running**. Use `-Cleanup` or delete manually after each run. Heavy tier (2400 scenario-runs) may take several hours and accrue Gemini API costs in addition to ACI compute.
