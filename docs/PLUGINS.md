# ChorusGraph Plug-ins — Swappable Product Ports

One-page map of what you can swap on [`ChorusStack`](../chorusgraph/compose/stack.py) without
changing graph or scheduler code.

**Install:** `pip install chorusgraph` · **Vector retrieval:** `pip install "chorusgraph[retrieval]"`  
**Full install guide:** [`INSTALL.md`](INSTALL.md)

| Port | Default | Swap examples | Swap method |
|------|---------|---------------|-------------|
| **Cache** (`CacheBackend`) | `PrismCacheBackend` | `RedisCacheBackend` | `with_cache()` |
| **Memory** (`MemoryBackend`) | `CortexMemoryBackend` | Disable with `enable_memory=False` | stack field |
| **Tools** (`ToolBackend`) | Finance tool registry | Custom `ToolRegistry` | `resolve_tools()` |
| **Retrieval** (`RetrievalBackend`) | `KeywordRetrievalBackend` | `PrismRAGRetrievalBackend` | `with_retrieval()` |

Engine-fixed (not swappable): PrismLang projection, resonance bus, BSP scheduler, envelope channels,
checkpointer/ledger defaults (override via stack fields).

---

## Cache swap

```python
from chorusgraph.compose import ChorusStack, RedisCacheBackend

stack = ChorusStack.defaults(tenant_id="acme").with_cache(
    RedisCacheBackend(tenant_id="acme", redis_url="redis://localhost:6379/0")
)
runtime = stack.to_cache_runtime()  # for node-entry cache interceptor
```

---

## Memory swap

```python
stack = ChorusStack.defaults(tenant_id="acme", enable_memory=False)  # cache-only graphs
```

---

## Retrieval — keyword default

Zero dependencies. Generalizes token-overlap scoring over **your** corpus (not hardcoded domain data).

```python
from chorusgraph.compose import ChorusStack, KeywordRetrievalBackend

corpus = [{"id": "1", "topic": "fx", "text": "USD EUR exchange rate", "source": "kb"}]
kw = KeywordRetrievalBackend()
kw.index(corpus)

stack = ChorusStack.defaults(tenant_id="acme").with_retrieval(kw)
handler = stack.to_retrieve_handler(topic="fx", top_k=3)
```

---

## Retrieval — PrismRAG plugin (vector + taxonomy)

### Architecture

```
ChorusStack.with_retrieval(PrismRAGRetrievalBackend)
        │
        ├─ index(corpus) ──► Chroma collection (+ optional PrismRAGPatch remap)
        │
        └─ to_retrieve_handler() ──► make_retrieve_handler
                                      └─► resonance_rerank (64-d PrismLang substrate)
```

### Install

```bash
pip install "chorusgraph[retrieval]"
export PRISMRAG_LICENSE_KEY="..."   # optional — enables taxonomy remap
```

### Constructor reference

```python
PrismRAGRetrievalBackend(
    embedder=None,              # default: PrismlangOnnxEmbedder()
    mapping=None,               # {"categories": [...], "rules": [...]}
    license_key=None,           # or PRISMRAG_LICENSE_KEY env
    alpha=0.25,                 # remap strength (PrismRAGPatch)
    collection_name="chorusgraph_retrieval",
    category_fn=None,           # Callable[[str], Optional[str]]
)
```

### Full example

```python
from chorusgraph.compose import ChorusStack, PrismRAGRetrievalBackend
from chorusgraph.embedders import PrismlangOnnxEmbedder

mapping = {
    "categories": [{"slug": "policy", "label": "Policy"}],
    "rules": [{"word": "refund", "category_slug": "policy"}],
}

backend = PrismRAGRetrievalBackend(
    embedder=PrismlangOnnxEmbedder(),
    mapping=mapping,
    category_fn=lambda t: "policy" if "refund" in (t or "").lower() else None,
)
backend.index(corpus)

stack = ChorusStack.defaults(tenant_id="acme").with_retrieval(backend)
retrieve_node = stack.to_retrieve_handler(topic="policy", top_k=6)
```

### Degradation matrix

| Condition | Behavior |
|-----------|----------|
| `chromadb` missing | Internal `KeywordRetrievalBackend`; warning logged |
| No `PRISMRAG_LICENSE_KEY` | Vector search OK; remap disabled; warning logged |
| `prismrag_patch` import fails | Raw Chroma query; warning logged |

### Protocol (bring your own backend)

```python
from chorusgraph.compose.ports import RetrievalBackend, is_retrieval_backend

class MyBackend:
    name = "custom"
    _chorusgraph_retrieval_backend = True

    def index(self, corpus): ...
    def retrieve(self, topic, query, *, top_k=6) -> list[dict]: ...
```

Required chunk keys: `id`, `topic`, `text`, `source`, `category_slug`, `score`.

---

## Compose API exports

```python
from chorusgraph.compose import (
    ChorusStack,
    KeywordRetrievalBackend,
    PrismRAGRetrievalBackend,
    RedisCacheBackend,
    PrismCacheBackend,
    RetrievalBackend,
    is_retrieval_backend,
)
```

---

## Related docs

- [`INSTALL.md`](INSTALL.md) — pip extras, step-by-step PrismRAG guide
- [`COMPOSE.md`](COMPOSE.md) — fixed vs swappable layers
- [`CACHE_PROFILES.md`](CACHE_PROFILES.md) — retrieve hop cache archetypes
- [`handoffs/handoffPrismRagPlugin.md`](../handoffs/handoffPrismRagPlugin.md) — design handoff
