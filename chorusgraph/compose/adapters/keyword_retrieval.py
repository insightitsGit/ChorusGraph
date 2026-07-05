"""Zero-dependency keyword retrieval backend (E5 default)."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence


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
    """Corpus-agnostic token-overlap retriever — no chromadb or license required."""

    name = "keyword"
    _chorusgraph_retrieval_backend = True

    def __init__(self) -> None:
        self._corpus: List[Dict[str, Any]] = []

    def index(self, corpus: Sequence[Dict[str, Any]]) -> None:
        self._corpus = [dict(c) for c in corpus]

    def retrieve(self, topic: str, query: str, *, top_k: int = 6) -> List[Dict[str, Any]]:
        if not self._corpus:
            return []
        scored: List[tuple[int, Dict[str, Any]]] = []
        for doc in self._corpus:
            score = _score_doc(topic, query, doc)
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda x: -x[0])
        picks = scored[:top_k] if scored else [(0, self._corpus[-1])]
        return [_chunk_record(d, score=float(s)) for s, d in picks]
