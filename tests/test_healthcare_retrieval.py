"""T4 — Healthcare retrieve handler uses vector KB + resonance rerank hook."""

from __future__ import annotations

import pytest

chromadb = pytest.importorskip("chromadb")

from benchmark.healthcare.retrieval import make_healthcare_retrieve_handler, vector_retrieve_fn
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime


def test_vector_retrieve_fn_no_llm():
    docs = vector_retrieve_fn("diabetes", "metformin eGFR 55")
    assert docs
    assert docs[0]["id"]


def test_make_healthcare_retrieve_handler_rerank(monkeypatch):
    runtime = FinanceRuntime(tenant_id="test-hc-retrieve")
    handler = make_healthcare_retrieve_handler(runtime, top_k=3)
    state = {
        "message": "metformin contrast eGFR",
        "topic": "diabetes",
        "query_vector_64": runtime.cache._projector.project(runtime.cache._embedder.embed("x")).vector.tolist(),
    }
    update = handler(state)
    assert update.get("retrieved")
    assert update.get("kb_context")
    assert "retrieve=" in update.get("rule_chain", [""])[0]
