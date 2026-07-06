"""Structured Cortex recall — vector + graph facts, not JSON prose."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StructuredRecallContext:
    """L3 memory handoff for internal hops — ONNX vector + provenance facts."""

    query_vector_64: List[float]
    category_slug: str
    evidence: List[Dict[str, Any]]
    confidence: float
    freshness: Optional[datetime]
    subgraph_hash: str
    cache_hit: bool = False
    replay_answer: Optional[str] = None
    query_vector_128: Optional[List[float]] = None

    @property
    def fact_text(self) -> str:
        return "; ".join(e.get("fact", "") for e in self.evidence if e.get("fact"))

    def to_memory_state(self) -> Dict[str, Any]:
        """Partial state update — vectors and facts, not LLM prose."""
        state: Dict[str, Any] = {
            "memory_recall": self.fact_text or self.replay_answer,
            "memory_confidence": self.confidence,
            "memory_freshness": self.freshness.isoformat() if self.freshness else None,
            "memory_cache_hit": self.cache_hit,
            "memory_vector_64": self.query_vector_64,
            "memory_subgraph_hash": self.subgraph_hash,
            "memory_evidence": list(self.evidence),
        }
        if self.query_vector_128 is not None:
            state["memory_vector_128"] = list(self.query_vector_128)
        return state


def evidence_from_explain(explain: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in getattr(explain, "evidence", None) or []:
        out.append(
            {
                "fact": getattr(item, "fact", ""),
                "confidence": float(getattr(item, "confidence", 0.0) or 0.0),
                "source_id": getattr(item, "source_id", None),
                "recorded_at": (
                    item.recorded_at.isoformat()
                    if getattr(item, "recorded_at", None) is not None
                    else None
                ),
            }
        )
    return out
