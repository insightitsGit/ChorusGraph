# Benchmark result fixtures

Archived snapshots of `benchmark/results/` for regression and audit.

## Refresh

```bash
python -m benchmark.archive_results --copy-jsonl
python -m benchmark.archive_results --run h10_final_pilot_40 --copy-jsonl
```

## Canonical runs (post-fix)

| Run | Use for |
|-----|---------|
| `h10_final_pilot_40` | **All fixes** — cache score, cross-session memory, belief calibration |
| `cache_seed_pilot_40` | Cache-only validation |
| `h10_volume` | Volume A/B **invalid for cache** (pre-seed-fix) |

See `MANIFEST.json` for full catalog and `ARCHIVE_META.json` per run.
