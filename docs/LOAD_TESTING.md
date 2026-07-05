# ChorusGraph Load Test Results (E7)

Run locally:

```powershell
python -m benchmark.load --requests 40 --levels 1,2,4,8
```

## Methodology

- **Workload:** native graph invoke (single-node increment) — engine overhead without live Gemini.
- **Metrics:** throughput (req/s), P50/P95 latency, success rate at increasing concurrency.
- **Soak:** run `--requests 1000 --levels 4` and monitor process memory externally.

## Notes

This is the **separate load/traffic test** (E7), distinct from H9/H10 per-task A/B benchmarks.
Production envelope requires Azure sizing + Director SLO sign-off.
