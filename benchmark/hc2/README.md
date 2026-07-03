# Container D — ChorusGraph healthcare multi-agent

**Reference doc:** [`docs/FINANCE_MULTIAGENT_CHORUS.md`](../../docs/FINANCE_MULTIAGENT_CHORUS.md) (same wiring pattern as F)

Fair comparison pair: **C vs D** (healthcare clinical pipeline).

## Quick topology

```
MISS: vector_ingress → cache_gate → intake → … → writer
HIT:  vector_ingress → cache_gate → writer (cached clinical state)
```

## Key files

| File | Role |
|------|------|
| `nodes.py` | Hop handlers, routing, envelope updates |
| `artifacts.py` | Envelope store + resolve + handoffs |
| `cache_helpers.py` | Clinical cache seed/restore |
| `trace.py` | JSONL hop trace (`CHORUS_D_TRACE=1`) |
| `runner.py` | Per-session runtime + graph build |

## Run

```powershell
python -m benchmark.run_multiagent --cases 18 --seed 42 --band 40 --container both
```
