"""Zero-dependency keyword retrieval backend (E5 default)."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence

from chorusgraph.compose.retrieval_stats import RetrievalStats


def _score_doc(topic: str, query: str, doc: Dict[str, Any]) -> int:
    q = f"{topic} {query}".lower()
    text = str(doc.get("text") or "").lower()
    score = sum(1 for token in q.split() if len(token) > 3 and token in text)
    if topic.lower() in str(doc.get("topic") or "").lower():
        score += 2
    return score


def _chunk_record(doc: Dict[str, Any], *, score: float = 0.0) -> Dict[str, Any]:
    slug = str(doc.get("category_slug") or doc.get("topic") or "general")
    return {
        "id": doc["id"],
        "topic": doc.get("topic", ""),
        "text": doc.get("text", ""),
        "source": doc.get("source", ""),
        "category_slug": slug,
        "score": score,
    }


class KeywordRetrievalBackend:
    """Corpus-agnostic token-overlap retriever — no chromadb or license required.

    Supports optional partitions / ``warm`` / ``stats`` for the warm chunk-vector
    API surface (no vectors; always ready once indexed).
    """

    name = "keyword"
    _chorusgraph_retrieval_backend = True

    def __init__(self) -> None:
        self._partitions: Dict[str, List[Dict[str, Any]]] = {}
        self._versions: Dict[str, Optional[str]] = {}
        self._ready: Dict[str, bool] = {}
        self._stats = RetrievalStats()
        # Legacy alias used by older call sites / tests
        self._corpus: List[Dict[str, Any]] = []

    def index(
        self,
        corpus: Sequence[Dict[str, Any]],
        *,
        partition: str = "default",
        version: Optional[str] = None,
    ) -> None:
        rows = [dict(c) for c in corpus]
        self._partitions[partition] = rows
        self._versions[partition] = version
        self._ready[partition] = bool(rows)
        self._stats.partition_versions[partition] = version
        if partition == "default":
            self._corpus = rows
        self._stats.ready_partitions = tuple(
            p for p, ok in self._ready.items() if ok
        )

    def retrieve(
        self,
        topic: str,
        query: str,
        *,
        top_k: int = 6,
        partition: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        part = partition or "default"
        corpus = self._partitions.get(part) or (self._corpus if part == "default" else [])
        if not corpus:
            return []
        scored: List[tuple[int, Dict[str, Any]]] = []
        for doc in corpus:
            score = _score_doc(topic, query, doc)
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda x: -x[0])
        picks = scored[:top_k] if scored else [(0, corpus[-1])]
        return [_chunk_record(d, score=float(s)) for s, d in picks]

    def warm(self, *, partition: Optional[str] = None) -> None:
        t0 = time.perf_counter()
        if partition is not None:
            parts = [partition]
        else:
            parts = list(self._partitions.keys()) or ["default"]
        for part in parts:
            rows = self._partitions.get(part) or []
            self._ready[part] = bool(rows)
            self._stats.partition_versions[part] = self._versions.get(part)
        self._stats.ready_partitions = tuple(p for p, ok in self._ready.items() if ok)
        self._stats.last_warm_ms = (time.perf_counter() - t0) * 1000.0

    def is_ready(self, *, partition: Optional[str] = None) -> bool:
        if partition is not None:
            return bool(self._ready.get(partition))
        if not self._partitions:
            return bool(self._corpus)
        return all(self._ready.get(p) for p in self._partitions)

    def stats(self) -> RetrievalStats:
        return self._stats
