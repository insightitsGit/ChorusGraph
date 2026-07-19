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

### Optional: warm chunk vectors (1.1.0+) / public 384-d read (1.3.0)

**When to use:** Production RAG hubs that reuse a stable knowledge corpus across turns (site KB,
guidelines, docs agents). Especially when catalog/DB rows change independently of markdown docs.

**Benefits:** Lower retrieve latency (no per-turn corpus re-encode), predictable cold starts via
worker `warm_retrieval()`, separate invalidation domains (`kb_markdown` vs `catalog`), and opt-in
rerank that never silently re-embeds chunks. Does **not** replace L1 `cache_gate` or education
short-circuits. Defaults remain 1.0.x-compatible until you enable the flags.

```python
backend.index(markdown_corpus, partition="kb_markdown", version="docs-2026-07-13")
backend.index(catalog_rows, partition="catalog", version="cat-42")

stack = ChorusStack.defaults(tenant_id="acme").with_retrieval(backend)
stack.warm_retrieval(partition="kb_markdown")
assert stack.retrieval_ready(partition="kb_markdown")

# PrismShine zero-re-embed: read warm 384-d vectors without re-encoding
recs = stack.get_chunk_vectors(["chunk-1", "chunk-2"], partition="kb_markdown")
# recs["chunk-1"].vector_384  # len 384; .version / .encoder_artifact_id when available

# Fact-correction / STALE_CACHE_REUSE: bump version (no auto re-index)
stack.bump_partition_version("kb_markdown")  # returns int; stored as str

retrieve_node = stack.to_retrieve_handler(
    topic="site_kb",
    top_k=6,
    partition="kb_markdown",
    rerank_policy="vectors_only",      # or "require" in prod/CI
    require_chunk_vectors=True,
)
# After warm retrieve: backend.stats().corpus_embeds == 0; query_embeds increments per call
```

See [`ADR-005-warm-chunk-vectors.md`](ADR-005-warm-chunk-vectors.md).

### Degradation matrix

| Condition | Behavior |
|-----------|----------|
| `chromadb` missing | Internal `KeywordRetrievalBackend`; warning logged |
| No `PRISMRAG_LICENSE_KEY` | Vector search OK; remap disabled; warning logged |
| `prismrag_patch` import fails | Raw Chroma query; warning logged |

### Protocol (bring your own backend)

```python
from chorusgraph.compose.ports import RetrievalBackend, RetrievalStats, is_retrieval_backend

class MyBackend:
    name = "custom"
    _chorusgraph_retrieval_backend = True

    def index(self, corpus, *, partition="default", version=None): ...
    def retrieve(self, topic, query, *, top_k=6, partition=None) -> list[dict]: ...
    def warm(self, *, partition=None): ...
    def is_ready(self, *, partition=None) -> bool: ...
    def stats(self) -> RetrievalStats: ...
    def bump_partition_version(self, partition="default") -> int: ...  # optional (1.3.0)
    def get_chunk_vectors(self, chunk_ids, *, partition="default") -> dict: ...  # optional
```

Required chunk keys: `id`, `topic`, `text`, `source`, `category_slug`, `score`.
Warm vector path should also attach `vector_64` (len 64). `warm` / `is_ready` / `stats` /
`bump_partition_version` / `get_chunk_vectors` are optional for custom backends; stack helpers
no-op or raise clearly when missing.

---

## Companion: PrismGuard

[PrismGuard](https://pypi.org/project/prismguard/) ([**0.1.4**](https://pypi.org/project/prismguard/0.1.4/)) is an **optional companion package** for prompt-injection firewalling. It is **not** one of the five `ChorusStack` ports — install it separately and wire a guard node in your graph.

| | ChorusGraph ports | PrismGuard |
|--|-------------------|------------|
| Install | `pip install chorusgraph` (+ extras) | `pip install "prismguard[prism,guard-model]==0.1.4"` |
| Wiring | `with_cache` / `with_retrieval` / … | Graph node via `make_guard_handler` |
| Role | Orchestration, cache, RAG, memory | Pre-LLM input check (+ optional output scan) |

```bash
pip install chorusgraph "prismguard[prism,guard-model]==0.1.4"
prismguard-model download   # ~705 MB ONNX from GitHub Release v0.1.2
```

```python
from chorusgraph import Graph, START, END, ChorusStack
from chorusgraph.core.node import dict_node_adapter
from prismguard.integrations.chorusgraph import (
    create_checker_from_env,
    make_guard_handler,
    route_after_guard,
)

checker = create_checker_from_env()
guard_fn = make_guard_handler(checker)

g = Graph(tenant_id="acme", graph_id="guarded")
g.add_node("guard", dict_node_adapter(guard_fn, hop="guard"))
# g.add_conditional_edges("guard", route_after_guard, {"end": END, "continue": "retrieve"})
# Place guard before cache-gated / retrieve hops
```

**Order:** guard → retrieve / LLM. Blocked prompts should not seed the semantic cache.

After the writer / LLM hop, call PrismGuard’s `scan_output(answer)` if you need response exfiltration checks.

| Resource | URL |
|----------|-----|
| PyPI (latest) | https://pypi.org/project/prismguard/ |
| PyPI 0.1.4 | https://pypi.org/project/prismguard/0.1.4/ |
| GitHub | https://github.com/insightitsGit/PrismGuard |
| Integration guide | https://github.com/insightitsGit/PrismGuard/blob/main/docs/integration-guide.md |
| ONNX model release | https://github.com/insightitsGit/PrismGuard/releases/tag/v0.1.2 |

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

- [`INSTALL.md`](INSTALL.md) — pip extras, step-by-step PrismRAG guide, PrismGuard companion install
- [`COMPOSE.md`](COMPOSE.md) — fixed vs swappable layers
- [`CACHE_PROFILES.md`](CACHE_PROFILES.md) — retrieve hop cache archetypes
- [`handoffs/handoffPrismRagPlugin.md`](../handoffs/handoffPrismRagPlugin.md) — design handoff
