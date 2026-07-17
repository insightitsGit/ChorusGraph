# ChorusGraph use cases

Concrete scenarios for the product stack:

| Layer / pattern | CLI | When to pick it |
|-----------------|-----|-----------------|
| **Cache (L1)** | `chorusgraph-use-cases cache` | Repeat / paraphrase queries |
| **Warm chunks (L2)** | `chorusgraph-use-cases warm_chunks` | Stable KB RAG — index once per partition/version |
| **PrismCortex (L3)** | `chorusgraph-use-cases cortex` | User/session facts — recall ingress, async digest |
| **ReAct** | `chorusgraph-use-cases react` | Exploration / multi-tool discovery |
| **Plan-and-Solve** | `chorusgraph-use-cases plan_solve` | Fixed checklist, known tools |
| **Reflection** | `chorusgraph-use-cases reflection` | Quality-sensitive drafts |
| **Multi-agent** | `chorusgraph-use-cases multi_agent` | Researcher → Writer → Validator |

Not LangGraph — native `chorusgraph.core.Graph` + `ChorusStack` ports.

## Run (no API key)

```bash
pip install -e .
chorusgraph-use-cases                 # all seven
chorusgraph-use-cases cache
chorusgraph-use-cases warm_chunks
chorusgraph-use-cases cortex
chorusgraph-use-cases --list
```

## Warm chunks (ADR-005)

```python
from chorusgraph.compose import ChorusStack, KeywordRetrievalBackend
# or PrismRAGRetrievalBackend for vector_64 on chunks

backend = KeywordRetrievalBackend()
backend.index(kb_docs, partition="kb_markdown", version="docs-v1")
backend.index(catalog, partition="catalog", version="cat-v1")
stack = ChorusStack.defaults(tenant_id="acme").with_retrieval(backend)
stack.warm_retrieval(partition="kb_markdown")
assert stack.retrieval_ready(partition="kb_markdown")
# PrismRAG: rerank_policy="vectors_only", require_chunk_vectors=True
```

Catalog bumps must not invalidate `kb_markdown`. See [`docs/ADR-005-warm-chunk-vectors.md`](../../../docs/ADR-005-warm-chunk-vectors.md).

## PrismCortex — right usage

| Do | Don't |
|----|--------|
| `recall_structured` at ingress → `memory_confidence` / `memory_evidence` | Put user prefs in L1 whole-answer cache |
| `schedule_digest` **after** the response (async) | Call `digest()` synchronously on the hot path |
| Empty recall → continue (no fake fallback) | Re-inject the full chat transcript every hop |

```python
# Live wiring (needs GEMINI for real Cortex)
from chorusgraph.compose import ChorusStack
stack = ChorusStack.defaults(tenant_id="acme")  # memory=CortexMemoryBackend
mem = stack.resolve_memory()
# ingress: mem.recall_structured(query)
# egress:  mem.schedule_digest(payload, source_id=turn_id)
```

Live demo: `chorusgraph-finance-memory`. Teaching stub (offline): `chorusgraph-use-cases cortex`.

## Interactive walkthrough

[website/demo.html](../../../website/demo.html) — step 5 cache · step 6 warm/Cortex · step 7 pattern tabs.

## Live Gemini

```bash
pip install "chorusgraph[gemini]"
export GEMINI_API_KEY=...
chorusgraph-finance-patterns   # cache_gate + ReAct / Plan-Solve / Reflection
chorusgraph-finance-memory     # checkpoints + cross-session Cortex
```
