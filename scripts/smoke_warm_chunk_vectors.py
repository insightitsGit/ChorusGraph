"""Smoke: optional warm chunk vectors — index once, query-only retrieve, no silent re-embed."""

from __future__ import annotations

import sys
from pathlib import Path

# Prefer the local workspace package over an older site-packages install.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> int:
    from chorusgraph.compose import ChorusStack, KeywordRetrievalBackend

    print("== smoke: keyword partitions ==")
    kw = KeywordRetrievalBackend()
    kw.index(
        [{"id": "md1", "topic": "kb", "text": "PrismCache reduces LLM API costs with semantic recall", "source": "md"}],
        partition="kb_markdown",
        version="docs-v1",
    )
    kw.index(
        [{"id": "cat1", "topic": "catalog", "text": "Hotel AI Web Agent 5499 one-time", "source": "db"}],
        partition="catalog",
        version="cat-v1",
    )
    stack = ChorusStack.defaults(tenant_id="smoke-warm").with_retrieval(kw)
    stack.warm_retrieval(partition="kb_markdown")
    assert stack.retrieval_ready(partition="kb_markdown"), "kb_markdown not ready"
    assert stack.retrieval_ready(partition="catalog"), "catalog not ready"
    md_hits = kw.retrieve("kb", "PrismCache costs", top_k=1, partition="kb_markdown")
    cat_hits = kw.retrieve("catalog", "hotel", top_k=1, partition="catalog")
    assert md_hits[0]["id"] == "md1", md_hits
    assert cat_hits[0]["id"] == "cat1", cat_hits
    handler = stack.to_retrieve_handler(
        topic="kb",
        partition="kb_markdown",
        rerank_policy="vectors_only",
    )
    update = handler({"message": "PrismCache LLM", "topic": "kb"})
    assert update.get("retrieved"), update
    assert any("rerank_policy=vectors_only" in r for r in update.get("rule_chain", []))
    print("  keyword OK:", md_hits[0]["id"], cat_hits[0]["id"], "rules=", update["rule_chain"])

    try:
        import chromadb  # noqa: F401
    except ImportError:
        print("== smoke: PrismRAG skipped (chromadb not installed) ==")
        print("SMOKE PASS (keyword only)")
        return 0

    print("== smoke: PrismRAG warm path ==")
    from chorusgraph.compose import PrismRAGRetrievalBackend
    from chorusgraph.embedders import PrismlangOnnxEmbedder
    from chorusgraph.nodes.retrieve import resonance_rerank
    import numpy as np

    corpus = [
        {"id": "a", "topic": "cache", "text": "PrismCache caches LLM answers semantically across paraphrases", "source": "kb"},
        {"id": "b", "topic": "cache", "text": "Warm chunk vectors avoid re-encoding the knowledge corpus every turn", "source": "kb"},
        {"id": "c", "topic": "other", "text": "Unrelated weather forecast for Dallas Texas", "source": "kb"},
    ]
    backend = PrismRAGRetrievalBackend(
        embedder=PrismlangOnnxEmbedder(),
        collection_name="smoke_warm_chunks",
        tenant_id="smoke-warm",
    )
    backend.index(corpus, partition="kb_markdown", version="v1")
    n_after_index = backend.stats().corpus_embeds
    assert n_after_index >= 3, n_after_index
    backend.stats().reset_counters()
    stack2 = ChorusStack.defaults(tenant_id="smoke-warm").with_retrieval(backend)
    stack2.warm_retrieval(partition="kb_markdown")
    assert stack2.retrieval_ready(partition="kb_markdown")
    assert backend.stats().corpus_embeds == 0, "warm must not re-encode"

    hits = backend.retrieve("cache", "How does PrismCache reduce LLM costs?", top_k=2, partition="kb_markdown")
    assert backend.stats().corpus_embeds == 0, backend.stats()
    assert backend.stats().query_embeds == 1, backend.stats()
    assert hits and "vector_64" in hits[0] and len(hits[0]["vector_64"]) == 64

    # Same version index is no-op
    backend.index(corpus, partition="kb_markdown", version="v1")
    assert backend.stats().corpus_embeds == 0

    # vectors_only rerank must not call embedder for chunks
    cache = stack2.resolve_cache().cache
    calls = {"n": 0}
    real = cache._embedder.embed

    def counting(text):
        calls["n"] += 1
        return real(text)

    cache._embedder.embed = counting
    q = real("PrismCache semantic cache")
    env = cache._projector.project(q)
    ranked, mode = resonance_rerank(
        cache,
        query_vector_64=np.asarray(env.vector, dtype=np.float32),
        chunks=hits,
        top_k=2,
        rerank_policy="vectors_only",
    )
    assert mode == "vectors", mode
    assert calls["n"] == 0, calls
    assert ranked and "resonance_score" in ranked[0]

    handler2 = stack2.to_retrieve_handler(
        topic="cache",
        partition="kb_markdown",
        rerank_policy="vectors_only",
        require_chunk_vectors=True,
    )
    out = handler2(
        {
            "message": "PrismCache reduce costs",
            "topic": "cache",
            "query_vector_64": list(env.vector),
        }
    )
    assert out.get("retrieved")
    assert any("rerank=vectors" in r for r in out.get("rule_chain", [])), out.get("rule_chain")

    print(
        "  prismrag OK: corpus_embeds_index=",
        n_after_index,
        "query_embeds=",
        backend.stats().query_embeds,
        "top=",
        hits[0]["id"],
        "rerank_mode=",
        mode,
    )
    print("SMOKE PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("SMOKE FAIL:", exc, file=sys.stderr)
        raise
