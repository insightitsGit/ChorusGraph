"""PrismRAG taxonomy mapping for the clinical benchmark corpus."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from benchmark.healthcare.kb import GUIDELINES

# Keyword → category rules derived from GUIDELINES text (inspectable, extensible).
CLINICAL_CATEGORY_RULES: List[Dict[str, str]] = [
    {"word": "hypertension", "category_slug": "hypertension"},
    {"word": "hyperkalemia", "category_slug": "hypertension"},
    {"word": "potassium", "category_slug": "hypertension"},
    {"word": "bp", "category_slug": "hypertension"},
    {"word": "ace", "category_slug": "hypertension"},
    {"word": "spironolactone", "category_slug": "hypertension"},
    {"word": "lisinopril", "category_slug": "hypertension"},
    {"word": "metformin", "category_slug": "diabetes"},
    {"word": "diabetes", "category_slug": "diabetes"},
    {"word": "egfr", "category_slug": "diabetes"},
    {"word": "contrast", "category_slug": "diabetes"},
    {"word": "hypoglycemia", "category_slug": "diabetes"},
    {"word": "warfarin", "category_slug": "anticoagulation"},
    {"word": "bleeding", "category_slug": "anticoagulation"},
    {"word": "inr", "category_slug": "anticoagulation"},
    {"word": "doac", "category_slug": "anticoagulation"},
    {"word": "statin", "category_slug": "lipids"},
    {"word": "ldl", "category_slug": "lipids"},
    {"word": "ascvd", "category_slug": "lipids"},
    {"word": "simvastatin", "category_slug": "lipids"},
    {"word": "clarithromycin", "category_slug": "safety"},
    {"word": "phenelzine", "category_slug": "safety"},
    {"word": "fluoxetine", "category_slug": "safety"},
    {"word": "serotonin", "category_slug": "safety"},
    {"word": "monitoring", "category_slug": "general"},
    {"word": "heart failure", "category_slug": "heart_failure"},
    {"word": "hfref", "category_slug": "heart_failure"},
    {"word": "empagliflozin", "category_slug": "heart_failure"},
    {"word": "ckd", "category_slug": "renal"},
    {"word": "ibuprofen", "category_slug": "renal"},
    {"word": "nsaid", "category_slug": "renal"},
]


@dataclass
class ClinicalMapping:
    """Local taxonomy mapper — same contract as ``prismrag_patch.mapping.Mapping``."""

    categories: List[Dict[str, str]] = field(default_factory=list)
    rules: List[Dict[str, str]] = field(default_factory=list)
    _word_to_cat: Dict[str, str] = field(default_factory=dict, repr=False)

    def build(self) -> "ClinicalMapping":
        self._word_to_cat = {
            str(r["word"]).lower().strip(): str(r["category_slug"])
            for r in self.rules
        }
        return self

    def assign_category(self, text: str) -> Optional[str]:
        lower = (text or "").lower()
        scores: Dict[str, int] = {}
        for word, slug in self._word_to_cat.items():
            if word in lower:
                scores[slug] = scores.get(slug, 0) + 1
        if not scores:
            return None
        return max(scores, key=lambda s: scores[s])


def _unique_topics() -> List[str]:
    topics = sorted({str(g["topic"]) for g in GUIDELINES})
    extra = ["heart_failure", "renal", "safety", "general", "lipids"]
    return sorted(set(topics) | set(extra))


def build_clinical_mapping_dict() -> Dict[str, Any]:
    """Mapping dict for ``PrismRAGPatch`` / ``ClinicalMapping``."""
    categories = [{"slug": t, "label": t.replace("_", " ").title()} for t in _unique_topics()]
    return {"categories": categories, "rules": list(CLINICAL_CATEGORY_RULES)}


@lru_cache(maxsize=1)
def build_clinical_mapping() -> ClinicalMapping:
    d = build_clinical_mapping_dict()
    return ClinicalMapping(categories=d["categories"], rules=d["rules"]).build()


def assign_clinical_category(text: str) -> Optional[str]:
    """Deterministic category assignment — no license required."""
    return build_clinical_mapping().assign_category(text)


def _ensure_prismrag_lib_on_path() -> bool:
    """Prefer local ``PrismRagLib`` checkout over any stale pip package."""
    candidates = [
        Path(__file__).resolve().parents[2].parent / "PrismRagLib",
        Path(r"C:\code\PrismRagLib"),
    ]
    for root in candidates:
        if (root / "prismrag_patch" / "mapping.py").is_file():
            path = str(root)
            if path not in sys.path:
                sys.path.insert(0, path)
            return True
    return False


def try_create_prismrag_patch(*, alpha: float = 0.25, adapter: str = "chroma"):
    """
    Instantiate ``PrismRAGPatch`` when ``PRISMRAG_LICENSE_KEY`` is set.

    Returns ``None`` if unset — callers use raw vector search without remap.
    """
    license_key = os.environ.get("PRISMRAG_LICENSE_KEY", "").strip()
    if not license_key:
        return None
    _ensure_prismrag_lib_on_path()
    try:
        from prismrag_patch import PrismRAGPatch
    except ImportError:
        return None
    return PrismRAGPatch(
        license_key=license_key,
        mapping=build_clinical_mapping_dict(),
        alpha=alpha,
        adapter=adapter,
    )


__all__ = [
    "CLINICAL_CATEGORY_RULES",
    "ClinicalMapping",
    "assign_clinical_category",
    "build_clinical_mapping",
    "build_clinical_mapping_dict",
    "try_create_prismrag_patch",
]
