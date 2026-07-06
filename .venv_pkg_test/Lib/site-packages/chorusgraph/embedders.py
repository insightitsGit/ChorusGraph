"""ChorusGraph embedder adapters — real semantic embeddings for cache gate."""

from __future__ import annotations

import numpy as np

from prism.cache.embedder import Embedder


class CountingEmbedder(Embedder):
    """Wraps an embedder and counts embed() calls (per-turn via reset_turn_calls)."""

    def __init__(self, inner: Embedder) -> None:
        self._inner = inner
        self.total_calls = 0
        self.turn_calls = 0

    @property
    def output_dim(self) -> int:
        return self._inner.output_dim

    def reset_turn_calls(self) -> None:
        self.turn_calls = 0

    def embed(self, text: str) -> np.ndarray:
        self.total_calls += 1
        self.turn_calls += 1
        return self._inner.embed(text)


class PrismlangOnnxEmbedder(Embedder):
    """
    Real all-MiniLM-L6-v2 embeddings via prismlang's ONNX encoder.

    Same model family as SentenceTransformerEmbedder; avoids sentence-transformers
    HF hub fragility while remaining semantically meaningful (not HashEmbedder).
    """

    def __init__(self) -> None:
        from prismlang.config import EMBED_DIM

        self._dim = EMBED_DIM

    @property
    def output_dim(self) -> int:
        return self._dim

    def embed(self, text: str) -> np.ndarray:
        from prismlang import encoder

        return encoder.encode(text).astype(np.float32)
