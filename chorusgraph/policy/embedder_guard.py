"""Embedder fail-loud guard — refuse HashEmbedder for cache measurement."""

from __future__ import annotations

import os
from typing import Any

import numpy as np

from prism.cache.embedder import Embedder, HashEmbedder

from chorusgraph.embedders import PrismlangOnnxEmbedder

CANARY_A = "What is your return policy for online orders?"
CANARY_B = "Tell me about the return policy for items bought online."
CANARY_MIN_COSINE = 0.5


def is_hash_embedder(embedder: Embedder) -> bool:
    return isinstance(embedder, HashEmbedder)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-12:
        return 0.0
    return float(np.dot(a, b) / denom)


def assert_semantic_embedder(embedder: Embedder) -> None:
    """
    Refuse to run cache gate / shadow unless a real semantic embedder is active.

    - Blocks HashEmbedder unless CHORUSGRAPH_ALLOW_HASH_EMBEDDER=1
    - Runs a canary pair; asserts cosine > 0.5
    """
    if is_hash_embedder(embedder):
        if os.environ.get("CHORUSGRAPH_ALLOW_HASH_EMBEDDER") == "1":
            return
        raise RuntimeError(
            "Refusing to run cache gate with HashEmbedder — embeddings are not "
            "semantically meaningful and shadow FP measurement would be worthless. "
            "Install sentence-transformers or use PrismlangOnnxEmbedder. "
            "Set CHORUSGRAPH_ALLOW_HASH_EMBEDDER=1 only for explicit CI plumbing tests."
        )

    va = embedder.embed(CANARY_A)
    vb = embedder.embed(CANARY_B)
    score = _cosine(va, vb)
    if score < CANARY_MIN_COSINE:
        raise RuntimeError(
            f"Embedder canary failed: cosine({CANARY_A!r}, {CANARY_B!r}) = {score:.4f} "
            f"< {CANARY_MIN_COSINE}. Embedder is not producing semantic similarity."
        )


def build_guarded_cache(
    tenant_id: str,
    *,
    embedder: Embedder | None = None,
) -> Any:
    """
    Build PrismCache with a guarded semantic embedder.

    Prefers an explicitly passed embedder; otherwise PrismlangOnnxEmbedder
    (real all-MiniLM-L6-v2 via ONNX — same model as SentenceTransformer default).
    """
    from prism.cache import PrismCache

    if embedder is None:
        embedder = PrismlangOnnxEmbedder()
    assert_semantic_embedder(embedder)
    return PrismCache.build(tenant_id=tenant_id, embedder=embedder)
