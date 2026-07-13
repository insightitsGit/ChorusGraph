# ADR-005: Optional warm chunk vectors (L2)

**Status:** Accepted · opt-in for next minor release  
**Date:** 2026-07-13  
**Related:** [`PLUGINS.md`](PLUGINS.md), [`COMPOSE.md`](COMPOSE.md), Website Hub dogfood RAG latency

## Context

Production Website Hub traces showed ~16 s turns on education-style RAG queries. Hotspots were not pgvector search:

- `prismlang_encode_chunks` ~6.7 s after catalog DB changes invalidated a shared markdown vector cache
- `prismapi_query` ~9 s re-embedding the corpus every turn
- `resonance_rerank` in ChorusGraph could also **silently re-embed** chunk text when `vector_64` was missing

ChorusGraph already had L1 answer cache (`cache_gate`) and L2 `RetrievalBackend.index()` / `retrieve()`, but:

1. Hubs often bypassed the retrieval port (custom `rag.py`)
2. The library did not treat **warm corpus chunk vectors** as a first-class, opt-in speed contract

## Decision

Ship **optional warm chunk vectors** as an additive L2 improvement:

| Mechanism | Role |
|-----------|------|
| `index(..., partition=, version=)` | Encode corpus once per partition/version |
| `warm()` / `is_ready()` / `ChorusStack.warm_retrieval()` | Process-boot readiness (not browser page load) |
| Chunks carry `vector_64` | Free Resonance rerank without hot-path embed |
| `RetrieveConfig.rerank_policy` | Opt-in: `vectors_only` / `require`; default `embed_missing` (1.0.x) |
| `RetrievalStats` | `query_embeds` vs `corpus_embeds` observability |

**Defaults stay 1.0.x-compatible.** Adopters enable the feature explicitly.

## Use cases

**Primary:** Production RAG chat / site hubs with a mostly stable markdown KB and a separately changing product catalog.

**Also:** multi-replica workers that need a ready probe; HC* guideline retrieve; any graph that reuses the same corpus across turns.

**Not primary:** greeting / deterministic education short-circuits (those should skip RAG entirely).

## Benefits

- **Latency** — avoid multi-second corpus re-encode on every retrieve
- **Predictability** — warm at worker boot; `retrieval_ready` before traffic
- **Cost** — embed corpus once per version; query-only on retrieve
- **Partition isolation** — catalog updates must not invalidate `kb_markdown`
- **Safe rerank** — opt-in policies stop silent N× chunk embeds
- **One runtime** — same `ChorusStack` retrieval port hubs can dogfood

## Non-goals

- Putting the whole KB into L1 PrismCache on every page load
- Replacing education short-circuit or L1 `cache_gate`
- Breaking 1.0.x by changing default rerank behavior in this release

## Consequences

- Built-in `KeywordRetrievalBackend` and `PrismRAGRetrievalBackend` implement `warm` / `is_ready` / `stats`
- Custom backends may omit those methods; stack helpers no-op / return ready
- Website Hub should wire `ChorusStack` retrieval + cache ports and call `warm_retrieval()` at startup (separate dogfood work)

## Enable recipe

```python
backend.index(markdown_corpus, partition="kb_markdown", version=kb_hash)
stack = ChorusStack.defaults(tenant_id="acme").with_retrieval(backend)
stack.warm_retrieval(partition="kb_markdown")
assert stack.retrieval_ready(partition="kb_markdown")

retrieve = stack.to_retrieve_handler(
    topic="site_kb",
    partition="kb_markdown",
    rerank_policy="vectors_only",
    require_chunk_vectors=True,
)
```
