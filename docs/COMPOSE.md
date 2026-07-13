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
| **L2 retrieval** | **Yes** | `KeywordRetrievalBackend` | `PrismRAGRetrievalBackend` — see [`PLUGINS.md`](PLUGINS.md) |
| **Persistence** | **Yes** | `SqlitePersistenceBackend` | `PostgresPersistenceBackend` — Enterprise license; see [`ENTERPRISE_READINESS.md`](ENTERPRISE_READINESS.md) |

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

Swap retrieval (PrismRAG plug-in) — full guide in [`INSTALL.md`](INSTALL.md):

```python
from chorusgraph.compose import PrismRAGRetrievalBackend
from chorusgraph.embedders import PrismlangOnnxEmbedder

backend = PrismRAGRetrievalBackend(embedder=PrismlangOnnxEmbedder(), mapping={...})
backend.index(corpus)
stack = ChorusStack.defaults(tenant_id="acme").with_retrieval(backend)
retrieve_node = stack.to_retrieve_handler(topic="policy", top_k=6)
```

**Optional warm chunk vectors** (opt-in, defaults unchanged): index with `partition`/`version`,
call `stack.warm_retrieval()` at worker boot, and use
`to_retrieve_handler(..., rerank_policy="vectors_only")`. Use when RAG reuses a stable KB and you
need lower latency / catalog-vs-docs invalidation isolation. Details: [`PLUGINS.md`](PLUGINS.md),
[`ADR-005-warm-chunk-vectors.md`](ADR-005-warm-chunk-vectors.md).

Enterprise Postgres persistence (offline license required):

```python
import os
from chorusgraph.compose import PostgresPersistenceBackend

stack = ChorusStack.defaults(tenant_id="acme").with_persistence(
    PostgresPersistenceBackend(dsn=os.environ["CHORUSGRAPH_PG_DSN"])
)
# Set CHORUSGRAPH_LICENSE_FILE to signed JSON with enterprise_persistence feature
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
| `retrieval` | `KeywordRetrievalBackend` (zero-deps keyword overlap) |
| `persistence` | `SqlitePersistenceBackend` (checkpoints + graph store) |

---

## Ports (`chorusgraph.compose.ports`)

| Protocol | Method surface |
|----------|------------------|
| `CacheBackend` | `embed`, `project_64`, `recall`, `recall_direct`, `seed` |
| `MemoryBackend` | `schedule_digest`, `recall_structured` |
| `ToolBackend` | `get`, `list_names` |
| `RetrievalBackend` | `retrieve`, `index` |
| `PersistenceBackend` | `make_checkpointer`, `make_graph_store` |

See [`PLUGINS.md`](../docs/PLUGINS.md) for defaults and swap options in one place.

Implement a port → pass instance on `ChorusStack(cache=...)` or `with_retrieval(...)`.

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
