"""Optional warm chunk-vector path — back-compat defaults + opt-in behavior."""

from __future__ import annotations

import numpy as np
import pytest

from chorusgraph.compose import ChorusStack, KeywordRetrievalBackend
from chorusgraph.nodes.retrieve import (
    MissingChunkVectorError,
    RetrieveConfig,
    make_retrieve_handler,
    resonance_rerank,
)


def test_keyword_partition_warm_ready_stats():
    backend = KeywordRetrievalBackend()
    backend.index(
        [{"id": "1", "topic": "kb", "text": "PrismCache reduces LLM costs", "source": "md"}],
        partition="kb_markdown",
        version="v1",
    )
    backend.index(
        [{"id": "p1", "topic": "catalog", "text": "Hotel agent 5499", "source": "db"}],
        partition="catalog",
        version="c1",
    )
    assert backend.is_ready(partition="kb_markdown")
    assert backend.is_ready(partition="catalog")
    hits = backend.retrieve("kb", "PrismCache costs", top_k=1, partition="kb_markdown")
    assert hits[0]["id"] == "1"
    catalog = backend.retrieve("catalog", "hotel", top_k=1, partition="catalog")
    assert catalog[0]["id"] == "p1"
    st = backend.stats()
    assert st.partition_versions["kb_markdown"] == "v1"
    assert "kb_markdown" in st.ready_partitions


def test_stack_warm_retrieval_helpers():
    backend = KeywordRetrievalBackend()
    backend.index([{"id": "1", "topic": "t", "text": "hello world token", "source": ""}])
    stack = ChorusStack.defaults(tenant_id="warm-kw").with_retrieval(backend)
    stack.warm_retrieval()
    assert stack.retrieval_ready() is True
    assert stack.retrieval_stats() is not None


def test_resonance_rerank_embed_missing_default_compat():
    from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

    runtime = FinanceRuntime(tenant_id="rerank-compat", enable_cortex=False)
    chunks = [{"text": "alpha document", "id": "1"}, {"text": "beta document", "id": "2"}]
    raw = runtime.cache._embedder.embed("alpha")
    env = runtime.cache._projector.project(raw)
    ranked, mode = resonance_rerank(
        runtime.cache,
        query_vector_64=np.asarray(env.vector, dtype=np.float32),
        chunks=chunks,
        top_k=2,
        rerank_policy="embed_missing",
    )
    assert mode == "embed_missing"
    assert len(ranked) == 2
    assert ranked[0]["resonance_score"] >= ranked[1]["resonance_score"]


def test_resonance_rerank_vectors_only_skips_embed():
    from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

    runtime = FinanceRuntime(tenant_id="rerank-skip", enable_cortex=False)
    calls = {"n": 0}
    real_embed = runtime.cache._embedder.embed

    def counting_embed(text):
        calls["n"] += 1
        return real_embed(text)

    runtime.cache._embedder.embed = counting_embed
    chunks = [
        {"text": "alpha", "id": "1", "score": 0.9},
        {"text": "beta", "id": "2", "score": 0.8},
    ]
    raw = real_embed("alpha")
    env = runtime.cache._projector.project(raw)
    ranked, mode = resonance_rerank(
        runtime.cache,
        query_vector_64=np.asarray(env.vector, dtype=np.float32),
        chunks=chunks,
        top_k=2,
        rerank_policy="vectors_only",
    )
    assert mode == "skip_missing_vectors"
    assert calls["n"] == 0
    assert [c["id"] for c in ranked] == ["1", "2"]


def test_resonance_rerank_require_raises():
    from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

    runtime = FinanceRuntime(tenant_id="rerank-req", enable_cortex=False)
    raw = runtime.cache._embedder.embed("q")
    env = runtime.cache._projector.project(raw)
    with pytest.raises(MissingChunkVectorError):
        resonance_rerank(
            runtime.cache,
            query_vector_64=np.asarray(env.vector, dtype=np.float32),
            chunks=[{"text": "x", "id": "1"}],
            top_k=1,
            rerank_policy="require",
        )


def test_resonance_rerank_with_preattached_vectors_no_embed():
    from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

    runtime = FinanceRuntime(tenant_id="rerank-vec", enable_cortex=False)
    calls = {"n": 0}
    real_embed = runtime.cache._embedder.embed

    def counting_embed(text):
        calls["n"] += 1
        return real_embed(text)

    runtime.cache._embedder.embed = counting_embed
    q_raw = real_embed("alpha")
    q_env = runtime.cache._projector.project(q_raw)
    a_raw = real_embed("alpha document")
    a_env = runtime.cache._projector.project(a_raw)
    b_raw = real_embed("zzz unrelated")
    b_env = runtime.cache._projector.project(b_raw)
    chunks = [
        {"id": "1", "text": "alpha document", "vector_64": list(a_env.vector)},
        {"id": "2", "text": "zzz unrelated", "vector_64": list(b_env.vector)},
    ]
    ranked, mode = resonance_rerank(
        runtime.cache,
        query_vector_64=np.asarray(q_env.vector, dtype=np.float32),
        chunks=chunks,
        top_k=2,
        rerank_policy="vectors_only",
    )
    assert mode == "vectors"
    assert calls["n"] == 0
    assert ranked[0]["id"] == "1"


def test_handler_rule_chain_includes_rerank_policy():
    backend = KeywordRetrievalBackend()
    backend.index(
        [{"id": "1", "topic": "kb", "text": "metformin egfr monitoring guide", "source": ""}]
    )
    stack = ChorusStack.defaults(tenant_id="handler-rules").with_retrieval(backend)
    handler = stack.to_retrieve_handler(
        topic="kb",
        top_k=1,
        partition="default",
        rerank_policy="vectors_only",
    )
    update = handler({"message": "metformin egfr", "topic": "kb"})
    rules = update.get("rule_chain") or []
    assert any("rerank_policy=vectors_only" in r for r in rules)
    assert any("partition=default" in r for r in rules)


def test_prismrag_warm_path_corpus_embeds_once():
    pytest.importorskip("chromadb")
    from chorusgraph.compose import PrismRAGRetrievalBackend
    from chorusgraph.embedders import PrismlangOnnxEmbedder

    corpus = [
        {
            "id": "a",
            "topic": "cache",
            "text": "PrismCache caches LLM answers semantically",
            "source": "kb",
        },
        {
            "id": "b",
            "topic": "cache",
            "text": "Warm vectors avoid re-encoding the corpus",
            "source": "kb",
        },
    ]
    backend = PrismRAGRetrievalBackend(
        embedder=PrismlangOnnxEmbedder(),
        collection_name="warm_chunk_test",
        tenant_id="warm-test",
    )
    backend.index(corpus, partition="kb_markdown", version="v1")
    n_corpus = backend.stats().corpus_embeds
    assert n_corpus >= 2
    backend.stats().reset_counters()
    backend.warm(partition="kb_markdown")
    assert backend.is_ready(partition="kb_markdown")
    assert backend.stats().corpus_embeds == 0
    hits = backend.retrieve("cache", "PrismCache semantic", top_k=2, partition="kb_markdown")
    assert backend.stats().corpus_embeds == 0
    assert backend.stats().query_embeds == 1
    assert hits
    assert "vector_64" in hits[0]
    assert len(hits[0]["vector_64"]) == 64
    # Same version re-index is a no-op
    backend.index(corpus, partition="kb_markdown", version="v1")
    assert backend.stats().corpus_embeds == 0


def test_make_retrieve_handler_require_chunk_vectors():
    from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

    runtime = FinanceRuntime(tenant_id="handler-req", enable_cortex=False)
    cfg = RetrieveConfig(
        category_slug="kb",
        top_k=1,
        rerank_policy="require",
        require_chunk_vectors=True,
    )

    def _fn(topic, query):
        return [
            {
                "id": "1",
                "text": "no vector",
                "topic": topic,
                "source": "",
                "category_slug": "kb",
                "score": 1.0,
            }
        ]

    handler = make_retrieve_handler(_fn, cache=runtime.cache, config=cfg)
    raw = runtime.cache._embedder.embed("q")
    env = runtime.cache._projector.project(raw)
    with pytest.raises(MissingChunkVectorError):
        handler({"message": "q", "query_vector_64": list(env.vector)})
