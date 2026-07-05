"""Deprecated shim — Chroma/PrismRAG construction lives in ``chorusgraph.compose.adapters``."""

from __future__ import annotations

from typing import Any, Dict, List

from benchmark.healthcare.retrieval import get_clinical_retrieval_backend


class GuidelineVectorStore:
    """Compat wrapper around ``PrismRAGRetrievalBackend`` for legacy callers."""

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    def load(self) -> None:
        """No-op — ``get_clinical_retrieval_backend`` indexes on first build."""

    def query(self, topic: str, query: str, *, top_k: int = 6) -> List[Dict[str, Any]]:
        return self._backend.retrieve(topic, query, top_k=top_k)


def get_guideline_vector_store(*, force_reload: bool = False) -> GuidelineVectorStore:
    backend = get_clinical_retrieval_backend(force_reload=force_reload)
    return GuidelineVectorStore(backend)


def retrieve_guidelines_vector(topic: str, query: str, *, top_k: int = 6) -> List[Dict[str, Any]]:
    return get_clinical_retrieval_backend().retrieve(topic, query, top_k=top_k)


__all__ = [
    "GuidelineVectorStore",
    "get_guideline_vector_store",
    "retrieve_guidelines_vector",
]
