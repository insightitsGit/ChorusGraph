"""T2 — Vector-indexed clinical KB (Chroma + embedder)."""

from __future__ import annotations

import pytest

chromadb = pytest.importorskip("chromadb")

from benchmark.healthcare.kb_vector import get_guideline_vector_store, retrieve_guidelines_vector


def test_vector_store_load_and_query_deterministic():
    store_a = get_guideline_vector_store(force_reload=True)
    hits_a = store_a.query("diabetes", "metformin eGFR contrast", top_k=3)
    hits_b = store_a.query("diabetes", "metformin eGFR contrast", top_k=3)
    assert hits_a
    assert [h["id"] for h in hits_a] == [h["id"] for h in hits_b]
    assert all(h.get("category_slug") for h in hits_a)


def test_retrieve_guidelines_vector_shape():
    docs = retrieve_guidelines_vector("hypertension", "hyperkalemia spironolactone", top_k=2)
    assert len(docs) <= 2
    assert docs[0]["id"]
    assert docs[0]["text"]
