"""L2 retrieve node — PrismRAG candidates + PrismResonance rerank."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence

import numpy as np

from chorusgraph.cache_gate.gate import cosine_similarity

RetrieveFn = Callable[[str, str], Sequence[Dict[str, Any]]]
RerankPolicy = Literal["embed_missing", "vectors_only", "require"]


@dataclass(frozen=True)
class RetrieveConfig:
    """Configuration for the built-in retrieve node.

    ``rerank_policy`` defaults to ``embed_missing`` (1.0.x compatible). Opt into
    warm chunk vectors with ``vectors_only`` or ``require`` (see ADR-005).
    """

    category_slug: str = "knowledge"
    top_k: int = 6
    amplitude_min: float = 0.001
    min_constructive_score: float = 0.0
    rerank_policy: RerankPolicy = "embed_missing"
    require_chunk_vectors: bool = False
    partition: Optional[str] = None


class MissingChunkVectorError(ValueError):
    """Raised when ``rerank_policy='require'`` or ``require_chunk_vectors`` and a chunk lacks ``vector_64``."""


def resonance_rerank(
    cache: Any,
    *,
    query_vector_64: np.ndarray,
    chunks: Sequence[Dict[str, Any]],
    top_k: int = 6,
    amplitude_min: float = 0.001,
    min_constructive_score: float = 0.0,
    rerank_policy: RerankPolicy = "embed_missing",
    require_chunk_vectors: bool = False,
) -> tuple[List[Dict[str, Any]], str]:
    """
    Rerank KB chunks using the shared 64-d PrismLang substrate.

    Returns ``(ranked_chunks, rerank_mode)`` where ``rerank_mode`` is one of
    ``vectors``, ``embed_missing``, ``skip_missing_vectors``.

    Policies:
    - ``embed_missing`` (default): missing ``vector_64`` → embed text (1.0.x behavior)
    - ``vectors_only``: never embed on hot path; if any chunk lacks vectors, keep backend order
    - ``require``: raise ``MissingChunkVectorError`` if any chunk lacks ``vector_64``
    """
    if not chunks or cache is None:
        return list(chunks), "skip_missing_vectors" if not chunks else "vectors"

    strict = require_chunk_vectors or rerank_policy == "require"
    missing = [c for c in chunks if c.get("vector_64") is None]
    if strict and missing:
        ids = [str(c.get("id") or "?") for c in missing[:5]]
        raise MissingChunkVectorError(
            f"retrieve require_chunk_vectors: {len(missing)} chunk(s) missing vector_64 "
            f"(examples: {ids})"
        )

    if rerank_policy == "vectors_only" and missing:
        out = [dict(c) for c in list(chunks)[:top_k]]
        return out, "skip_missing_vectors"

    query_vec = np.asarray(query_vector_64, dtype=np.float32).ravel()
    mode = "vectors"
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
            mode = "embed_missing"
        score = cosine_similarity(query_vec, np.asarray(vec, dtype=np.float32))
        if score >= min_constructive_score:
            scored.append((score, dict(chunk)))

    scored.sort(key=lambda x: x[0], reverse=True)
    out: List[Dict[str, Any]] = []
    for score, chunk in scored[:top_k]:
        chunk["resonance_score"] = score
        out.append(chunk)
    return out, mode


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

        rerank_mode = "none"
        vec = state.get("query_vector_64")
        if vec is not None and cache is not None:
            ranked, rerank_mode = resonance_rerank(
                cache,
                query_vector_64=np.asarray(vec, dtype=np.float32),
                chunks=raw_chunks,
                top_k=cfg.top_k,
                amplitude_min=cfg.amplitude_min,
                min_constructive_score=cfg.min_constructive_score,
                rerank_policy=cfg.rerank_policy,
                require_chunk_vectors=cfg.require_chunk_vectors,
            )
        else:
            ranked = list(raw_chunks[: cfg.top_k])

        rules = [
            f"retrieve={cfg.category_slug}",
            f"chunks={len(ranked)}",
            f"rerank={rerank_mode}",
            f"rerank_policy={cfg.rerank_policy}",
        ]
        if cfg.partition:
            rules.append(f"partition={cfg.partition}")
        return {
            "kb_context": ranked,
            "retrieved": ranked,
            "category_slug": cfg.category_slug,
            "rule_chain": rules,
        }

    return retrieve_node


__all__ = [
    "MissingChunkVectorError",
    "RetrieveConfig",
    "RerankPolicy",
    "make_retrieve_handler",
    "resonance_rerank",
]
