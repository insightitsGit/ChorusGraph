# Composable Product Stack

**Status:** Active · implements pluggable section backends on the native engine  
**See also:** [`TERMINOLOGY.md`](TERMINOLOGY.md), [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md)

---

## Thesis

ChorusGraph ships as **one ready-to-run product** — engine plus Prism stack attached by default.
Developers may **replace individual backends** (cache, memory, checkpoint, ledger, tools)
without forking the engine or re-wiring benchmarks by hand.

---

## Fixed vs swappable

| Layer | Swappable? | Default | Notes |
|-------|------------|---------|-------|
| BSP scheduler | **No** | `chorusgraph.core.scheduler` | Engine core |
| Envelope channels | **No** | `ChannelState` + `PrismEnvelope` | Engine core |
| PrismLang 64-d projection | **No** | Built into engine / gate | Tenant-seeded JL substrate |
| Resonance bus routing | **No** | `ResonanceBus` | Conditional edge routing |
| CHORUS transport interface | **No** | `TransportRouter` | Cross-region spine hook |
| **Semantic cache** | **Yes** | `PrismCacheBackend` | e.g. `RedisCacheBackend` |
| Sidecar metadata | **Yes** | `SidecarStore` | Paired with Prism cache |
| **L3 memory** | **Yes** | `CortexMemoryBackend` | Disable with `enable_memory=False` |
| **Checkpointer** | **Yes** | JSON file checkpointer | Postgres, SQLite, … |
| **Route ledger sink** | **Yes** | `SqliteLedgerSink` | Postgres, custom |
| **Tool registry** | **Yes** | Finance default registry | MCP / custom tools |

**Rule:** swapping cache does **not** remove PrismLang projection — external stores still
use engine embed/project for semantic paths unless the backend implements its own policy.

---

## `ChorusStack`

Single composition root passed to `Graph.compile(stack=...)`:

```python
from chorusgraph import Graph, START, END, ChorusStack
from chorusgraph.compose import RedisCacheBackend

# Full product — zero extra wiring
stack = ChorusStack.defaults(tenant_id="acme")

# Swap cache only; everything else stays Prism default
stack = ChorusStack.defaults(tenant_id="acme").with_cache(
    RedisCacheBackend(tenant_id="acme", redis_url="redis://localhost:6379/0")
)

g = Graph(tenant_id="acme", graph_id="demo")
# ... add nodes / edges ...
compiled = g.compile(stack=stack)
# Opt-in durability:
# compiled = g.compile(stack=stack, checkpointer=stack.resolve_checkpointer())
```

### Resolved defaults (`ChorusStack.defaults`)

| Port | Implementation |
|------|----------------|
| `cache` | `PrismCacheBackend` (guarded semantic embedder + PrismCache) |
| `sidecar` | In-memory `SidecarStore` |
| `memory` | `CortexMemoryBackend` (PrismCortex) |
| `checkpointer` | JSON file under `.chorusgraph/checkpoints/` |
| `ledger` | In-memory SQLite ledger |
| `tools` | Finance tool registry |

---

## Ports (`chorusgraph.compose.ports`)

| Protocol | Method surface |
|----------|------------------|
| `CacheBackend` | `embed`, `project_64`, `recall`, `recall_direct`, `seed` |
| `MemoryBackend` | `schedule_digest`, `recall_structured` |
| `ToolBackend` | `get`, `list_names` |

Implement a port → pass instance on `ChorusStack(cache=...)`.

Existing call sites (`gate()`, `seed_cache_entry()`) accept either a **`CacheBackend`**
or legacy **`PrismCache` + `SidecarStore`** pair.

---

## Benchmark / agent runtimes

`FinanceRuntime` wraps `ChorusStack` for FC/HC benchmarks:

```python
from chorusgraph.compose import ChorusStack, RedisCacheBackend
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

stack = ChorusStack.defaults(tenant_id="benchmark-f").with_cache(
    RedisCacheBackend(tenant_id="benchmark-f")
)
runtime = FinanceRuntime(tenant_id="benchmark-f", stack=stack, enable_cortex=False)
```

Graph node handlers keep using `runtime.cache` / `runtime.sidecar`; the stack resolves
the active backend.

---

## Enforcement

- `tests/test_compose_stack.py` — defaults, compile wiring, Redis swap
- `tests/test_fc_hc_no_langgraph.py` — FC/HC stay native engine

---

## Related ADRs

- [`ADR-004-native-runtime.md`](ADR-004-native-runtime.md) — native engine decision
- [`TERMINOLOGY.md`](TERMINOLOGY.md) — ChorusGraph vs LangGraph
