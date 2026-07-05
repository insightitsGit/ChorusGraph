# ChorusGraph Load Test Results (E7)

Run locally:

```powershell
python -m benchmark.load --requests 40 --levels 1,2,4,8
```

## Methodology

- **Workload:** native graph invoke (single-node increment) — engine overhead without live Gemini.
- **Metrics:** throughput (req/s), P50/P95 latency, success rate at increasing concurrency.
- **Soak:** run `--requests 1000 --levels 4` and monitor process memory externally.

## Local validation (2026-07-05, master post-E-track)

Command: `python -m benchmark.load --requests 40 --levels 1,2,4,8`

| Concurrency | Throughput (req/s) | P50 (ms) | P95 (ms) | Success |
|-------------|------------------|----------|----------|---------|
| 1 | 5106 | 0.05 | 0.12 | 100% |
| 2 | 14783 | 0.05 | 0.06 | 100% |
| 4 | 12938 | 0.05 | 0.11 | 100% |
| 8 | 9595 | 0.06 | 0.11 | 100% |

Engine-only workload (single-node graph, no Gemini). Production SLO sign-off still requires staging/Azure soak at Director targets.

## Notes

This is the **separate load/traffic test** (E7), distinct from H9/H10 per-task A/B benchmarks.
Production envelope requires Azure sizing + Director SLO sign-off.
