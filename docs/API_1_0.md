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
| `ChorusStack` | Composed cache + memory + ledger + **retrieval** stack |

## Plug-ins & retrieval (1.0)

| Symbol | Purpose |
|--------|---------|
| `KeywordRetrievalBackend` | Zero-dep default retrieval |
| `PrismRAGRetrievalBackend` | Chroma vector + optional taxonomy remap |
| `with_retrieval()` | Swap retrieval port on `ChorusStack` |
| `to_retrieve_handler()` | Ready-made retrieve node |

Import via `chorusgraph.compose` — see [`docs/INSTALL.md`](INSTALL.md) and [`docs/PLUGINS.md`](PLUGINS.md).

## Agents & planning (1.0)

| Symbol | Purpose |
|--------|---------|
| `Agent` | Unified agent — `pattern="react"` \| `"plan_solve"` \| `"reflection"` |
| `PlanPolicy` | Step/token budgets, `on_exhaust` behavior |
| `ReActOpts`, `PlanSolveOpts`, `ReflectionOpts` | Per-pattern knobs |
| `run_agent_loop` | Generic reason ↔ act ↔ route substrate |
| `AgentNode`, `agent_result_to_state` | Drop an `Agent` into a graph node |
| `run_react`, `run_plan_solve`, `run_reflection` | Convenience runners |

```python
from chorusgraph.agents import Agent, PlanPolicy
```

See [`docs/DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) §10–11. Belief-tier `BeliefPolicy` knobs are API-stable but disabled until calibration.

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
