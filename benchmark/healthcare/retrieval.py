"""Healthcare L2 retrieval — library ``RetrievalBackend`` + stack integration."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional, Sequence

from benchmark.healthcare.kb import GUIDELINES
from benchmark.healthcare.prismrag_mapping import assign_clinical_category, build_clinical_mapping_dict
from chorusgraph.compose.adapters.prismrag_retrieval import PrismRAGRetrievalBackend
from chorusgraph.embedders import PrismlangOnnxEmbedder
from chorusgraph.nodes.retrieve import RetrieveConfig, make_retrieve_handler

RetrieveFn = Callable[[str, str], Sequence[Dict[str, Any]]]

_backend_lock = threading.Lock()
_backend: Optional[PrismRAGRetrievalBackend] = None


def build_clinical_retrieval_backend() -> PrismRAGRetrievalBackend:
    """Clinical corpus on the library PrismRAG backend — domain config stays benchmark-owned."""
    backend = PrismRAGRetrievalBackend(
        embedder=PrismlangOnnxEmbedder(),
        mapping=build_clinical_mapping_dict(),
        category_fn=assign_clinical_category,
        collection_name="chorusgraph_clinical_guidelines",
    )
    backend.index(GUIDELINES)
    return backend


def get_clinical_retrieval_backend(*, force_reload: bool = False) -> PrismRAGRetrievalBackend:
    global _backend
    with _backend_lock:
        if _backend is None or force_reload:
            _backend = build_clinical_retrieval_backend()
        return _backend


def vector_retrieve_fn(topic: str, query: str) -> List[Dict[str, Any]]:
    """Vector/keyword driver — deterministic given embedder (no LLM)."""
    docs = get_clinical_retrieval_backend().retrieve(
        topic, query, top_k=RetrieveConfig().top_k
    )
    q_cat = assign_clinical_category(f"{topic} {query}")
    if q_cat:
        for doc in docs:
            doc.setdefault("query_category_slug", q_cat)
    return docs


def make_healthcare_retrieve_handler(
    runtime: Any,
    *,
    topic: str = "clinical_guidelines",
    top_k: int = 6,
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Built-in retrieve node for HC1/HC2 — library retrieval + PrismResonance rerank.

    Uses ``runtime.stack.to_retrieve_handler`` when the stack carries a retrieval backend;
    otherwise falls back to the process-global clinical backend.
    """
    stack = getattr(runtime, "stack", None)
    if stack is not None:
        if stack.retrieval is None:
            stack = stack.with_retrieval(get_clinical_retrieval_backend())
        return stack.to_retrieve_handler(topic=topic, top_k=top_k, runtime=runtime)

    cfg = RetrieveConfig(category_slug=topic, top_k=top_k)

    def _retrieve_fn(t: str, q: str) -> List[Dict[str, Any]]:
        return list(vector_retrieve_fn(t or topic, q))

    return make_retrieve_handler(
        _retrieve_fn,
        cache=runtime.cache,
        config=cfg,
    )


__all__ = [
    "build_clinical_retrieval_backend",
    "get_clinical_retrieval_backend",
    "make_healthcare_retrieve_handler",
    "vector_retrieve_fn",
]
