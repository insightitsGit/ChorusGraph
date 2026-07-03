# Azure Container benchmark (ACI)

MVP scenario matrix (FL1–HC2) runs on **Azure Container Instances** — not VMs.

Existing `chorus-benchmark` / `chorus-relay` ACIs in `chorus-rg-us` are **chorus-protocol** relay tests; this harness uses a separate image: `chorusgraph-mvp-benchmark`.

## Deploy + run (one command)

```powershell
cd c:\code\ChorusGraph
# Requires: az CLI logged in, GEMINI_API_KEY in .env
.\benchmark\azure\deploy_and_run.ps1 -Wait
```

Options:

| Flag | Default | Meaning |
|------|---------|---------|
| `-Tasks` | 12 | Tasks/cases per scenario |
| `-Scenarios` | all | `all`, `pairs`, `finance`, or `FL1,FC1,...` |
| `-SkipBuild` | off | Reuse existing ACR image |
| `-Wait` | off | Poll until done, download blob results |

## What happens

1. **`az acr build`** — builds `chorusacrd7a6d0.azurecr.io/chorusgraph-mvp-benchmark:latest`
2. **`az container create`** — one-shot ACI in `chorus-rg-us` (`chorus-mvp-benchmark`)
3. Container runs `python -m benchmark.run_scenarios` with comparison report
4. Results upload to **`stinsightitsprod01`** blob: `benchmark-results/mvp_scenarios/{run_id}/`

## Manual commands

```powershell
# Follow logs while running
az container logs -g chorus-rg-us -n chorus-mvp-benchmark --follow

# Download after run
.\benchmark\azure\fetch_results.ps1 -RunId 20260702_010203
```

## Image contents

- `benchmark/azure/Dockerfile` — Python 3.11 + `[dev,gemini,cortex]`
- `benchmark/azure/entrypoint.sh` — runs scenarios, prints report, uploads tarball to blob

## Local fallback (no Azure)

```powershell
python -m benchmark.run_scenarios --scenarios all --tasks 12
```
