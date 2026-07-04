"""Dual-path healthcare cache gate — fingerprint (judgment) then semantic (retrieval)."""

from __future__ import annotations

from typing import Any, Optional

from benchmark.healthcare.fingerprint import clinical_fingerprint_from_case
from benchmark.hc2.cache_helpers import cache_query_key
from benchmark.shared.healthcare_cache import CLINICAL_RETRIEVAL_SLUG, gate_clinical
from benchmark.healthcare_workload import HealthcareCase
from chorusgraph.sections.profiles import default_registry


def gate_healthcare_case(
    runtime: Any,
    case: HealthcareCase,
    *,
    coarse_threshold: float,
    verify_threshold: float,
    raw_embedding_384=None,
    projected_vector_64=None,
):
    """
    Cache gate for HC1/HC2.

    1. Fingerprint lookup (``clinical_judgment`` profile) — case-level key at gate time.
    2. Semantic fallback (``clinical_retrieval``) — paraphrase / repeat band.
    """
    registry = default_registry()
    fp = clinical_fingerprint_from_case(case)

    fp_decision = gate_clinical(
        runtime,
        query=fp,
        category_slug="clinical_judgment",
        profile=registry.get("clinical_judgment"),
        session_id=case.session_id,
        fingerprint_key=fp,
        coarse_threshold=coarse_threshold,
        verify_threshold=verify_threshold,
        raw_embedding_384=raw_embedding_384,
        projected_vector_64=projected_vector_64,
    )
    if fp_decision.is_hit:
        return fp_decision

    return gate_clinical(
        runtime,
        query=cache_query_key(case),
        category_slug=CLINICAL_RETRIEVAL_SLUG,
        profile=registry.get(CLINICAL_RETRIEVAL_SLUG),
        session_id=case.session_id,
        coarse_threshold=coarse_threshold,
        verify_threshold=verify_threshold,
        raw_embedding_384=raw_embedding_384,
        projected_vector_64=projected_vector_64,
    )


__all__ = ["gate_healthcare_case"]
