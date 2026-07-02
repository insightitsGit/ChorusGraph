# Azure benchmark notes

ChorusGraph H9/H10 volume runs execute as **local Python** (`benchmark.run_volume`), not on Azure Container Instances.

The `chorus-benchmark` / `chorus-relay` ACIs in `chorus-rg-us` run the separate **chorus-protocol** image (`chorusacrd7a6d0.azurecr.io/chorus-protocol:latest`) — cross-region vector relay tests, not this finance A/B harness.

## Run H10 volume benchmark

```powershell
cd c:\code\ChorusGraph
$env:BENCHMARK_RUN_LABEL = 'H10'
python -m benchmark.run_volume --tasks 1000 --bands 40,60 --output-dir benchmark/results/h10_volume
python -m benchmark.rebuild_analysis benchmark/results/h10_volume 40,60
python -m benchmark.generate_results_doc benchmark/results/h10_volume/aggregate_analysis.json
```

Requires `GEMINI_API_KEY` in `ChorusGraph/.env`. Resume is automatic if JSONL files exist.
