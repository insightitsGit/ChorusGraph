"""Warm-index chunk vector records (ADR-005 / PrismShine zero-re-embed)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ChunkVectorRecord:
    """Public read of a warm-index chunk's raw 384-d vector + partition version."""

    chunk_id: str
    vector_384: List[float]
    partition: str
    version: Optional[str]
    encoder_artifact_id: Optional[str] = None
