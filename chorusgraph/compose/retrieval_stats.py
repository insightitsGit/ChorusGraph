"""Observability for optional warm chunk-vector retrieval (L2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RetrievalStats:
    """Counters for query vs corpus embeds and partition warmth."""

    query_embeds: int = 0
    corpus_embeds: int = 0
    partition_versions: Dict[str, Optional[str]] = field(default_factory=dict)
    last_warm_ms: float = 0.0
    ready_partitions: tuple[str, ...] = ()

    def reset_counters(self) -> None:
        self.query_embeds = 0
        self.corpus_embeds = 0


__all__ = ["RetrievalStats"]
