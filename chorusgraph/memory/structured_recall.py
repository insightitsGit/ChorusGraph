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
    """Map Cortex explain evidence — includes 0.3.0 correction metadata when present."""
    out: List[Dict[str, Any]] = []
    for item in getattr(explain, "evidence", None) or []:
        row: Dict[str, Any] = {
            "fact": getattr(item, "fact", ""),
            "confidence": float(getattr(item, "confidence", 0.0) or 0.0),
            "source_id": getattr(item, "source_id", None),
            "recorded_at": (
                item.recorded_at.isoformat()
                if getattr(item, "recorded_at", None) is not None
                else None
            ),
        }
        # PrismCortex 0.3.0 — correction / supersession fields (optional)
        vf = getattr(item, "valid_from", None)
        if vf is not None:
            row["valid_from"] = vf.isoformat() if hasattr(vf, "isoformat") else vf
        if getattr(item, "supersedes_prior", None) is not None:
            row["supersedes_prior"] = bool(item.supersedes_prior)
        if getattr(item, "prior_value", None) is not None:
            row["prior_value"] = item.prior_value
        out.append(row)
    return out
