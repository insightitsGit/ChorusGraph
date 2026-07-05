# Handoffback E5 — Durable Persistence

**Status:** Complete on branch `P1_Enterprice1`

## Summary

E5 adds SQLite-backed durable Cortex GraphStore (survives restart), versioned migrations, backup/restore helpers, and product-wide `forget_subject` across graph, ledger, cache sidecar, and checkpoints.

## How to run

```powershell
pytest tests/test_persistence.py -v
```

## Proposed E6

Cross-tenant leakage test suite + per-tenant resource limits.
