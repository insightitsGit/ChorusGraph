"""ChorusGraph embedder adapters — real semantic embeddings for cache gate."""

from __future__ import annotations

import numpy as np

from prism.cache.embedder import Embedder


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
