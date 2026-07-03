# FC2 — ChorusGraph finance multi-agent (native engine)

**ChorusGraph native** — `chorusgraph.core.Graph` only (no LangGraph). Policy: [`docs/TERMINOLOGY.md`](../../docs/TERMINOLOGY.md).

**Reference doc:** [`docs/FINANCE_MULTIAGENT_CHORUS.md`](../../docs/FINANCE_MULTIAGENT_CHORUS.md)

Fair comparison pair: **FL2 vs FC2** (same workload).

## Quick topology

```
MISS: vector_ingress → cache_gate → researcher → tool → writer → validator
HIT:  vector_ingress → cache_gate → writer → validator
```

## Key files

| File | Role |
|------|------|
| `nodes.py` | Graph, routing, hop handlers |
| `artifacts.py` | Envelope store + resolve + handoff |
| `cache_helpers.py` | Multi-tool cache recovery on hit |
| `trace.py` | JSONL hop trace (`CHORUS_F_TRACE=1`) |
| `runner.py` | Session runner (does not clear session cache) |

## Run

```powershell
python -m benchmark.run_finance_multiagent --tasks 12 --seed 42 --band 40 --container both
```

See full checklist and code patterns in the main doc.
