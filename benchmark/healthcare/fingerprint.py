"""Clinical fingerprint keying — structured equivalence, not free text (H21 T3 + PrismRAG)."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Sequence

from benchmark.healthcare_workload import HealthcareCase

# Depth bands for fingerprint field growth (named constants — not magic numbers).
FINGERPRINT_DEPTH_CITED_IDS = 4
FINGERPRINT_DEPTH_INTERACTIONS = 6


def _bin_lab_value(name: str, value: float) -> str:
    """Documented bins for common labs used in synthetic corpus."""
    bins: Dict[str, Sequence[float]] = {
        "k": (3.5, 4.0, 4.5, 5.0, 5.5),
        "egfr": (30, 45, 60, 90),
        "bp_sys": (120, 130, 140, 160),
        "bp_dia": (80, 90, 100),
    }
    key = name.lower()
    if key not in bins:
        return f"{name}={value:.1f}"
    edges = bins[key]
    for i, edge in enumerate(edges):
        if value < edge:
            return f"{name}<{edge}"
    return f"{name}>={edges[-1]}"


def _extract_labs(facts: str) -> List[str]:
    """Parse simple lab patterns from intake facts text."""
    out: List[str] = []
    text = facts or ""
    for m in re.finditer(r"K\+?\s*([0-9]+(?:\.[0-9]+)?)", text, re.I):
        out.append(_bin_lab_value("k", float(m.group(1))))
    for m in re.finditer(r"eGFR\s*([0-9]+(?:\.[0-9]+)?)", text, re.I):
        out.append(_bin_lab_value("egfr", float(m.group(1))))
    for m in re.finditer(r"BP\s*([0-9]+)/([0-9]+)", text, re.I):
        out.append(_bin_lab_value("bp_sys", float(m.group(1))))
        out.append(_bin_lab_value("bp_dia", float(m.group(2))))
    return sorted(set(out))


def _cited_ids_signature(hop_artifacts: Optional[Dict[str, Any]]) -> List[str]:
    retrieve = (hop_artifacts or {}).get("retrieve") or {}
    cited = retrieve.get("cited_ids") or []
    return sorted(str(x) for x in cited if x)


def _interaction_severity_signature(hop_artifacts: Optional[Dict[str, Any]]) -> List[str]:
    drug_check = (hop_artifacts or {}).get("drug_check") or {}
    interactions = drug_check.get("interactions") or []
    severities: List[str] = []
    for row in interactions:
        if isinstance(row, dict) and row.get("severity"):
            severities.append(str(row["severity"]))
    return sorted(set(severities))


def _category_slugs_signature(
    hop_artifacts: Optional[Dict[str, Any]],
    retrieved: Optional[List[Dict[str, Any]]] = None,
) -> List[str]:
    """PrismRAG / retrieval category slugs attached to retrieved chunks."""
    slugs: set[str] = set()
    for doc in retrieved or []:
        slug = doc.get("category_slug") or doc.get("prismrag_category")
        if slug:
            slugs.add(str(slug))
    retrieve = (hop_artifacts or {}).get("retrieve") or {}
    for slug in retrieve.get("category_slugs") or []:
        if slug:
            slugs.add(str(slug))
    return sorted(slugs)


def _fingerprint_payload(
    *,
    pipeline_depth: int,
    drug_list: List[str],
    topic_s: str,
    labs: List[str],
    hop_artifacts: Optional[Dict[str, Any]] = None,
    retrieved: Optional[List[Dict[str, Any]]] = None,
    gate_phase: bool = False,
) -> Dict[str, Any]:
    """
    Build the structured equivalence payload.

    ``gate_phase=True`` uses only case-level fields (pre-pipeline cache gate).
    Seed phase adds retrieval-derived fields by depth band.
    """
    payload: Dict[str, Any] = {
        "drugs": drug_list,
        "topic": topic_s,
        "labs": labs,
        "pipeline_depth": int(pipeline_depth),
    }
    if gate_phase or pipeline_depth < FINGERPRINT_DEPTH_CITED_IDS:
        return payload

    payload["cited_ids_signature"] = _cited_ids_signature(hop_artifacts)
    cats = _category_slugs_signature(hop_artifacts, retrieved)
    if cats:
        payload["category_slugs_signature"] = cats

    if not gate_phase and pipeline_depth >= FINGERPRINT_DEPTH_INTERACTIONS:
        payload["interaction_severity_signature"] = _interaction_severity_signature(hop_artifacts)

    return payload


def clinical_fingerprint_from_case(case: HealthcareCase) -> str:
    """Gate-time fingerprint — case metadata only (before retrieve/drug_check hops)."""
    intake = {
        "drugs": list(case.drugs),
        "topic": case.topic,
        "facts": case.presentation,
    }
    return clinical_fingerprint(
        intake,
        pipeline_depth=case.pipeline_depth,
        drugs=case.drugs,
        topic=case.topic,
        gate_phase=True,
    )


def clinical_fingerprint(
    intake_artifact: Optional[Dict[str, Any]],
    *,
    pipeline_depth: int,
    drugs: Optional[List[str]] = None,
    topic: Optional[str] = None,
    hop_artifacts: Optional[Dict[str, Any]] = None,
    retrieved: Optional[List[Dict[str, Any]]] = None,
    gate_phase: bool = False,
) -> str:
    """
    Deterministic clinical equivalence key from structured intake fields.

    Depth bands (seed phase):
    - depth ≤ 2: drugs, topic, binned labs
    - depth ≥ 4: + cited_ids_signature, category_slugs_signature (PrismRAG)
    - depth ≥ 6: + interaction_severity_signature
    """
    art = intake_artifact or {}
    drug_list = sorted(str(d) for d in (drugs or art.get("drugs") or []) if d)
    topic_s = str(topic or art.get("topic") or "").strip().lower()
    facts = str(art.get("facts") or art.get("intake_summary") or "")
    labs = _extract_labs(facts)
    payload = _fingerprint_payload(
        pipeline_depth=pipeline_depth,
        drug_list=drug_list,
        topic_s=topic_s,
        labs=labs,
        hop_artifacts=hop_artifacts,
        retrieved=retrieved,
        gate_phase=gate_phase,
    )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
    return f"fp:{digest}"


__all__ = [
    "FINGERPRINT_DEPTH_CITED_IDS",
    "FINGERPRINT_DEPTH_INTERACTIONS",
    "clinical_fingerprint",
    "clinical_fingerprint_from_case",
]
