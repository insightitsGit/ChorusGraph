"""Clinical fingerprint keying — structured equivalence, not free text (H21 T3)."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Sequence


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
    for m in re.finditer(r"K\+?\s*([0-9.]+)", text, re.I):
        out.append(_bin_lab_value("k", float(m.group(1))))
    for m in re.finditer(r"eGFR\s*([0-9.]+)", text, re.I):
        out.append(_bin_lab_value("egfr", float(m.group(1))))
    for m in re.finditer(r"BP\s*([0-9]+)/([0-9]+)", text, re.I):
        out.append(_bin_lab_value("bp_sys", float(m.group(1))))
        out.append(_bin_lab_value("bp_dia", float(m.group(2))))
    return sorted(set(out))


def clinical_fingerprint(
    intake_artifact: Optional[Dict[str, Any]],
    *,
    pipeline_depth: int,
    drugs: Optional[List[str]] = None,
    topic: Optional[str] = None,
) -> str:
    """
    Deterministic clinical equivalence key from structured intake fields.

    Paraphrase of same case => same fingerprint. One changed lab/drug => different key.
    """
    art = intake_artifact or {}
    drug_list = sorted(str(d) for d in (drugs or art.get("drugs") or []) if d)
    topic_s = str(topic or art.get("topic") or "").strip().lower()
    facts = str(art.get("facts") or art.get("intake_summary") or "")
    labs = _extract_labs(facts)
    payload = {
        "drugs": drug_list,
        "topic": topic_s,
        "labs": labs,
        "pipeline_depth": int(pipeline_depth),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
    return f"fp:{digest}"


__all__ = ["clinical_fingerprint"]
