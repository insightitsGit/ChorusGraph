"""Smoke test for chroma_local_rag example -- offline, no API keys."""

from __future__ import annotations

from pathlib import Path

import pytest

chromadb = pytest.importorskip("chromadb")

from chorusgraph.compose import ChorusStack

from chorusgraph.examples.chroma_local_rag.graph import (
    build_retrieval_backend,
    load_corpus,
)

_SAMPLE = Path(__file__).resolve().parents[1] / "chorusgraph/examples/chroma_local_rag/sample_docs.txt"


def test_retrieve_handler_returns_chunks():
    corpus = load_corpus(_SAMPLE)
    backend = build_retrieval_backend(corpus, collection_name="test_chroma_local_rag")
    stack = ChorusStack.defaults(tenant_id="chroma-rag-test").with_retrieval(backend)
    handler = stack.to_retrieve_handler(topic="faq", top_k=3)
    update = handler({"message": "What is the refund policy?", "topic": "faq"})
    assert update.get("retrieved")
    assert len(update["retrieved"]) >= 1
    texts = " ".join(str(c.get("text", "")) for c in update["retrieved"])
    assert "refund" in texts.lower()
