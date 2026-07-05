# ChorusGraph 1.0 Public API

**Package:** `chorusgraph` · **Version:** 1.0.0

## Core runtime

| Symbol | Purpose |
|--------|---------|
| `Graph`, `CompiledGraph` | Build and run native agent graphs |
| `NodeContext`, `START`, `END` | Node handlers and graph terminals |
| `wrap` | Attach Route Ledger to a compiled graph |

## Cache & memory

| Symbol | Purpose |
|--------|---------|
| `gate`, `seed_cache_entry` | Cache gate evaluation and seeding |
| `CortexMemoryService`, `get_cortex_service` | L3 Cortex memory |
| `ChorusStack` | Composed cache + memory + ledger stack |

## Persistence & lifecycle (E5)

| Symbol | Purpose |
|--------|---------|
| `SqliteGraphStore` | Durable Cortex graph |
| `DataLifecycleManager` | Right-to-forget across layers |
| `migrate_file` | Schema migrations |

## Enterprise modules (E2–E6)

| Module | Purpose |
|--------|---------|
| `chorusgraph.resilience` | Retries, breakers, typed errors |
| `chorusgraph.security` | Tool sandbox, TLS policy, PII |
| `chorusgraph.observability` | Logs, traces, health endpoints |
| `chorusgraph.tenant` | Isolation and quotas |

Import the frozen surface via:

```python
from chorusgraph.public import Graph, wrap, TenantContext
```

Internal modules (`core.scheduler`, adapter internals) are **not** public API.
