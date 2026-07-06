"""ONNX embed + PrismLang 64-d projection for internal hops."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np


def project_from_raw(cache: Any, raw_384: np.ndarray) -> Tuple[np.ndarray, Any]:
    """Project a precomputed 384-d embedding — no ONNX embed."""
    raw = np.asarray(raw_384, dtype=np.float32).ravel()
    envelope = cache._projector.project(raw)
    return raw, envelope


def project_text(
    cache: Any,
    text: str,
    *,
    raw_384: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, Any]:
    """
    Project query text through ONNX embedder + JL projector (cache_gate substrate).

    When raw_384 is provided, skips embedding (ingress reuse).
  """
    if raw_384 is None:
        raw = cache._embedder.embed(text)
    else:
        raw = np.asarray(raw_384, dtype=np.float32).ravel()
    envelope = cache._projector.project(raw)
    return raw, envelope


def raw_from_state(state: Dict[str, Any]) -> Optional[np.ndarray]:
    """Load shared 384-d vector from graph state (set at vector_ingress)."""
    raw = state.get("raw_embedding_384")
    if raw is None:
        return None
    return np.asarray(raw, dtype=np.float32)


def vector_64_from_state(state: Dict[str, Any]) -> Optional[np.ndarray]:
    """Load shared 64-d projection from graph state (set at vector_ingress)."""
    vec = state.get("query_vector_64")
    if vec is None:
        return None
    return np.asarray(vec, dtype=np.float32)
