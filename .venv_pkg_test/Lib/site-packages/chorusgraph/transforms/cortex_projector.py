"""Cortex-native 128-d projection from shared 384-d ingress (H13)."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional, Tuple

import numpy as np


@lru_cache(maxsize=32)
def _cortex_prism_projector(tenant_id: str, k: int = 128):
    from prismcortex.adapters.prism import PrismLangProjector

    return PrismLangProjector(tenant_id=tenant_id, k=k)


def project_cortex_from_raw(
    tenant_id: str,
    text: str,
    raw_384: np.ndarray,
    *,
    k: int = 128,
) -> Tuple[str, np.ndarray, List[str]]:
    """
    Project precomputed MiniLM 384-d → Cortex native k-d (default 128).

    Skips ONNX re-embed; applies taxonomy spherical blend + JL reduction only.
    """
    wrapper = _cortex_prism_projector(tenant_id, k)
    p = wrapper._p
    v = np.asarray(raw_384, dtype=np.float32).ravel()
    if v.shape[0] != p._P.shape[1]:
        raise ValueError(f"expected {p._P.shape[1]}-d raw embedding, got {v.shape[0]}")

    slug = p.taxonomy.infer_category(text)
    e_i = p.taxonomy.direction_vector(slug)
    raw_blend = (1.0 - p.alpha) * v + p.alpha * float(np.linalg.norm(v)) * e_i
    v_prime = raw_blend / max(float(np.linalg.norm(raw_blend)), 1e-12)
    p_raw = p._P @ v_prime
    vec = (p_raw / max(float(np.linalg.norm(p_raw)), 1e-12)).astype(np.float32)
    rule_chain = [
        "ingress_raw_384 (no re-embed)",
        f"category_inference -> slug={slug!r}",
        f"spherical_blend(alpha={p.alpha:.3f}) -> v_prime",
        f"JL_reduction(seed=sha256({tenant_id!r}), k={k}) -> p",
    ]
    return slug, vec, rule_chain


def project_cortex_text(
    tenant_id: str,
    text: str,
    *,
    k: int = 128,
) -> Tuple[str, np.ndarray, List[str]]:
    """Full Cortex path (embed + project) — fallback when raw_384 unavailable."""
    from prismlang import encoder

    raw = encoder.encode(text).astype(np.float32)
    return project_cortex_from_raw(tenant_id, text, raw, k=k)
