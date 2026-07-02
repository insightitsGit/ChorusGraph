"""ONNX embed + PrismLang 64-d projection for internal hops."""

from __future__ import annotations

from typing import Any, Tuple

import numpy as np


def project_text(cache: Any, text: str) -> Tuple[np.ndarray, Any]:
    """
    Project query text through the same ONNX embedder + JL projector as cache_gate.

    Returns (raw_embedding_384, envelope) where envelope.vector is 64-d.
    """
    raw = cache._embedder.embed(text)
    envelope = cache._projector.project(raw)
    return np.asarray(raw, dtype=np.float32), envelope
