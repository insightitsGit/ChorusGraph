# Handoffback E4 — Observability

**Status:** Complete on branch `P1_Enterprice1`

## Summary

Structured JSON logging with correlation/run_id, OTel-compatible trace export from Route Ledger (`trace_id == run_id`), runtime metrics, `/health` `/ready` `/metrics` HTTP probes, and operator runbooks.

## How to run

```powershell
pytest tests/test_observability.py -v
python -c "from chorusgraph.observability import start_health_server; start_health_server(); input()"
```

## Proposed E5

Postgres Cortex GraphStore, schema migrations, backup/restore, right-to-forget.
