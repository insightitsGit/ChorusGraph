# ChorusGraph plug-in ports

One-page map of what you can swap on [`ChorusStack`](../chorusgraph/compose/stack.py) without
changing graph or scheduler code.

| Port | Default | Swap examples | Notes |
|------|---------|---------------|-------|
| **Cache** (`CacheBackend`) | `PrismCacheBackend` | `RedisCacheBackend` | Semantic + exact cache; `with_cache()` |
| **Memory** (`MemoryBackend`) | `CortexMemoryBackend` | Disable with `enable_memory=False` | L3 structured recall |
| **Tools** (`ToolBackend`) | Finance tool registry | Custom `ToolRegistry` | `resolve_tools()` |
| **Retrieval** (`RetrievalBackend`) | `KeywordRetrievalBackend` | `PrismRAGRetrievalBackend` | L2 KB search; `with_retrieval()` |

Engine-fixed (not swappable): PrismLang projection, resonance bus, BSP scheduler, envelope channels,
checkpointer/ledger defaults (override via stack fields).

## Retrieval

```python
from chorusgraph.compose import ChorusStack, KeywordRetrievalBackend, PrismRAGRetrievalBackend
from chorusgraph.embedders import PrismlangOnnxEmbedder

# Zero-dependency default (keyword overlap on an indexed corpus)
kw = KeywordRetrievalBackend()
kw.index([{"id": "1", "topic": "fx", "text": "USD EUR rate", "source": "kb"}])
stack = ChorusStack.defaults(tenant_id="acme").with_retrieval(kw)
retrieve_node = stack.to_retrieve_handler(topic="fx", top_k=3)

# Licensed vector + taxonomy remap (requires chromadb; optional PRISMRAG_LICENSE_KEY)
prism = PrismRAGRetrievalBackend(
    embedder=PrismlangOnnxEmbedder(),
    mapping={"categories": [...], "rules": [...]},
    category_fn=lambda text: None,
)
prism.index(corpus)
stack = ChorusStack.defaults(tenant_id="acme").with_retrieval(prism)
```

Without `chromadb`, `PrismRAGRetrievalBackend` logs a warning and delegates retrieve/index to an
internal keyword backend. Without `PRISMRAG_LICENSE_KEY`, vector search still runs but taxonomy remap
is disabled.

Install optional deps: `pip install chorusgraph[retrieval]` (chromadb).

See also: [`docs/COMPOSE.md`](COMPOSE.md), [`docs/CACHE_PROFILES.md`](CACHE_PROFILES.md) §4.
