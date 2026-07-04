"""Healthcare L2 retrieval — vector KB + ``make_retrieve_handler`` integration."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from benchmark.healthcare.kb_vector import retrieve_guidelines_vector
from benchmark.healthcare.prismrag_mapping import assign_clinical_category
from chorusgraph.nodes.retrieve import RetrieveConfig, make_retrieve_handler

RetrieveFn = Callable[[str, str], Sequence[Dict[str, Any]]]


def vector_retrieve_fn(topic: str, query: str) -> List[Dict[str, Any]]:
    """PrismRAG/Chroma vector driver — deterministic given embedder (no LLM)."""
    docs = retrieve_guidelines_vector(topic, query, top_k=RetrieveConfig().top_k)
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
    Built-in retrieve node for HC1/HC2 — vector KB + PrismResonance rerank.

    Wraps ``chorusgraph.nodes.retrieve.make_retrieve_handler``; LLM summarization
    stays in the scenario retrieve_node wrapper.
    """
    cfg = RetrieveConfig(category_slug=topic, top_k=top_k)

    def _retrieve_fn(t: str, q: str) -> List[Dict[str, Any]]:
        return list(vector_retrieve_fn(t or topic, q))

    return make_retrieve_handler(
        _retrieve_fn,
        cache=runtime.cache,
        config=cfg,
    )


__all__ = [
    "make_healthcare_retrieve_handler",
    "vector_retrieve_fn",
]
