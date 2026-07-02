"""Healthcare benchmark tools — real KB lookup + interaction dataset."""

from __future__ import annotations

from typing import Any, Dict, List

from benchmark.healthcare.kb import DRUG_INTERACTIONS, GUIDELINES


def retrieve_guidelines(topic: str, query: str, *, top_k: int = 3) -> List[Dict[str, Any]]:
    """Keyword retrieval over bundled guideline corpus (stand-in for pgvector KB)."""
    q = f"{topic} {query}".lower()
    scored: List[tuple[int, dict]] = []
    for doc in GUIDELINES:
        text = doc["text"].lower()
        score = sum(1 for token in q.split() if len(token) > 3 and token in text)
        if topic.lower() in doc["topic"]:
            score += 2
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:top_k]] or [GUIDELINES[-1]]


def check_drug_interactions(drugs: List[str]) -> List[Dict[str, Any]]:
    """Lookup interaction pairs from bundled dataset."""
    pairs: List[Dict[str, Any]] = []
    normalized = [d.lower().strip() for d in drugs if d]
    for i, a in enumerate(normalized):
        for b in normalized[i + 1 :]:
            key = (a, b) if (a, b) in DRUG_INTERACTIONS else (b, a)
            if key in DRUG_INTERACTIONS:
                row = dict(DRUG_INTERACTIONS[key])
                row["pair"] = list(key)
                pairs.append(row)
    return pairs
