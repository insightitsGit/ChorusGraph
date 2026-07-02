"""Structured per-hop artifacts for Container D envelope handoffs."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from benchmark.healthcare.abstain import should_abstain

__all__ = [
    "bounded_docs",
    "compact_analyze",
    "compact_artifact",
    "compact_drug",
    "compact_intake",
    "compact_json",
    "compact_retrieve",
    "envelope_handoff",
    "parse_json_object",
    "resolve_envelope_artifact",
    "safety_handoff_user",
    "should_abstain",
    "store_envelope_artifact",
    "writer_handoff_user",
]


def compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def envelope_handoff(
    *,
    hop: str,
    envelope_id: Optional[str],
    hop_input: Optional[Dict[str, Any]] = None,
) -> str:
    """Chorus M2M handoff — envelope pointer + hop-local input only (no upstream blob)."""
    payload: Dict[str, Any] = {"hop": hop, "previous_envelope_id": envelope_id}
    if hop_input:
        payload["hop_input"] = hop_input
    return compact_json(payload)


def store_envelope_artifact(runtime: Any, envelope_id: str, artifact: Dict[str, Any]) -> None:
    """Persist artifact keyed by envelope_id for downstream resolution."""
    runtime.session_tool_cache[f"env:{envelope_id}"] = artifact


def resolve_envelope_artifact(runtime: Any, envelope_id: Optional[str]) -> Dict[str, Any]:
    if not envelope_id:
        return {}
    cached = runtime.session_tool_cache.get(f"env:{envelope_id}")
    return dict(cached) if isinstance(cached, dict) else {}


def bounded_docs(docs: List[Dict[str, Any]], *, max_chars: int = 180) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for doc in docs:
        text = str(doc.get("text") or "")
        if len(text) > max_chars:
            text = text[: max_chars - 3] + "..."
        out.append(
            {
                "id": str(doc.get("id") or ""),
                "source": str(doc.get("source") or ""),
                "excerpt": text,
            }
        )
    return out


_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_json_object(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    text = _JSON_FENCE_RE.sub("", text).strip()
    try:
        data = json.loads(text or "{}")
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
        else:
            return {}
    return data if isinstance(data, dict) else {}


def compact_intake(artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not artifact:
        return {}
    return {
        "facts": str(artifact.get("facts") or "")[:200],
        "drugs": list(artifact.get("drugs") or [])[:8],
        "question": str(artifact.get("question") or "")[:120],
    }


def compact_retrieve(artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not artifact:
        return {}
    return {
        "cited_ids": [c for c in (artifact.get("cited_ids") or []) if c][:8],
        "summary": str(artifact.get("summary") or "")[:200],
    }


def compact_analyze(artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not artifact:
        return {}
    return {
        "reasoning": str(artifact.get("reasoning") or "")[:200],
        "uncertainties": list(artifact.get("uncertainties") or [])[:4],
    }


def compact_drug(artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not artifact:
        return {}
    severities: List[Dict[str, Any]] = []
    for row in list(artifact.get("interactions") or [])[:6]:
        if isinstance(row, dict):
            severities.append(
                {
                    "pair": row.get("pair"),
                    "severity": row.get("severity"),
                }
            )
    return {
        "summary": str(artifact.get("summary") or "")[:150],
        "severities": severities,
    }


def compact_artifact(source_hop: str, artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Compact artifact by the hop that produced it (not the consuming hop)."""
    if not artifact:
        return {}
    compactors = {
        "intake": compact_intake,
        "retrieve": compact_retrieve,
        "analyze": compact_analyze,
        "drug_check": compact_drug,
        "safety": lambda a: {
            "verdict": str(a.get("verdict") or ""),
            "reason": str(a.get("reason") or "")[:150],
        },
    }
    fn = compactors.get(source_hop)
    return fn(artifact) if fn else artifact


def safety_handoff_user(
    *,
    envelope_id: Optional[str],
    hop_artifacts: Dict[str, Dict[str, Any]],
) -> str:
    """Safety sees envelope pointer + compact evidence snapshot (not full tree)."""
    retrieve = hop_artifacts.get("retrieve")
    return envelope_handoff(
        hop="safety",
        envelope_id=envelope_id,
        hop_input={
            "facts": compact_intake(hop_artifacts.get("intake")),
            "cited_ids": compact_retrieve(retrieve).get("cited_ids") or [],
            "retrieve_summary": compact_retrieve(retrieve).get("summary") or "",
            "analysis": compact_analyze(hop_artifacts.get("analyze")),
            "drug": compact_drug(hop_artifacts.get("drug_check")),
        },
    )


def writer_handoff_user(
    *,
    envelope_id: Optional[str],
    hop_artifacts: Dict[str, Dict[str, Any]],
) -> str:
    """Writer sees envelope pointer + compact facts (not growing transcript)."""
    retrieve = hop_artifacts.get("retrieve")
    drug = hop_artifacts.get("drug_check")
    safety = hop_artifacts.get("safety") or {}
    return envelope_handoff(
        hop="writer",
        envelope_id=envelope_id,
        hop_input={
            "verdict": str(safety.get("verdict") or ""),
            "reason": str(safety.get("reason") or "")[:150],
            "facts": compact_intake(hop_artifacts.get("intake")),
            "cited_ids": compact_retrieve(retrieve).get("cited_ids") or [],
            "drug_summary": compact_drug(drug).get("summary") or "",
            "drug_severities": compact_drug(drug).get("severities") or [],
        },
    )
