"""L2 retrieve node — PrismRAG candidates + PrismResonance rerank."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

from chorusgraph.cache_gate.gate import cosine_similarity

RetrieveFn = Callable[[str, str], Sequence[Dict[str, Any]]]


@dataclass(frozen=True)
class RetrieveConfig:
    """Configuration for the built-in retrieve node."""

    category_slug: str = "knowledge"
    top_k: int = 6
    amplitude_min: float = 0.001
    min_constructive_score: float = 0.0


def resonance_rerank(
    cache: Any,
    *,
    query_vector_64: np.ndarray,
    chunks: Sequence[Dict[str, Any]],
    top_k: int = 6,
    amplitude_min: float = 0.001,
    min_constructive_score: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Rerank KB chunks using the shared 64-d PrismLang substrate.

    Projects chunk text through the same JL projector as L1 cache_gate, then scores
    with full-precision cosine (same verify stage as ``gate()`` §8.1). When chunks
    are pre-indexed in ``cache._resonance``, use ``cache._resonance.query`` instead
    (hub RAG path).
    """
    if not chunks or cache is None:
        return list(chunks)

    query_vec = np.asarray(query_vector_64, dtype=np.float32).ravel()

    scored: List[tuple[float, Dict[str, Any]]] = []
    for chunk in chunks:
        vec = chunk.get("vector_64")
        if vec is None:
            text = str(chunk.get("text") or chunk.get("content") or "")
            if not text.strip():
                continue
            raw = cache._embedder.embed(text)
            env = cache._projector.project(raw)
            vec = env.vector
        score = cosine_similarity(query_vec, np.asarray(vec, dtype=np.float32))
        if score >= min_constructive_score:
            scored.append((score, dict(chunk)))

    scored.sort(key=lambda x: x[0], reverse=True)
    out: List[Dict[str, Any]] = []
    for score, chunk in scored[:top_k]:
        chunk["resonance_score"] = score
        out.append(chunk)
    return out


def make_retrieve_handler(
    retrieve_fn: RetrieveFn,
    *,
    cache: Any,
    config: Optional[RetrieveConfig] = None,
):
    """
    Built-in retrieve node factory (DESIGN v0.3 §4.3).

    ``retrieve_fn(topic, query) -> chunks`` is the PrismRAG/pgvector driver hook.
    """
    cfg = config or RetrieveConfig()

    def retrieve_node(state: Dict[str, Any]) -> Dict[str, Any]:
        message = state.get("message") or state.get("query") or ""
        topic = str(state.get("topic") or state.get("category_slug") or cfg.category_slug)
        raw_chunks = list(retrieve_fn(topic, message))

        vec = state.get("query_vector_64")
        if vec is not None and cache is not None:
            ranked = resonance_rerank(
                cache,
                query_vector_64=np.asarray(vec, dtype=np.float32),
                chunks=raw_chunks,
                top_k=cfg.top_k,
                amplitude_min=cfg.amplitude_min,
                min_constructive_score=cfg.min_constructive_score,
            )
        else:
            ranked = list(raw_chunks[: cfg.top_k])

        return {
            "kb_context": ranked,
            "retrieved": ranked,
            "category_slug": cfg.category_slug,
            "rule_chain": [f"retrieve={cfg.category_slug}", f"chunks={len(ranked)}"],
        }

    return retrieve_node


__all__ = ["RetrieveConfig", "make_retrieve_handler", "resonance_rerank"]
