"""Container D graph state — vector ingress, cache gate, envelope sequence."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from prismlang import PrismEnvelope

from benchmark.container_c.runner import HealthcareState


class HealthcareVectorState(HealthcareState, total=False):
    """Full D state: clinical pipeline + Chorus vector/cache channels."""

    message: str
    raw_embedding_384: List[float]
    query_vector_64: List[float]
    prism_sequence: Annotated[List[PrismEnvelope], operator.add]
    vector_hops: Annotated[List[Dict[str, Any]], operator.add]
    cache_hit: Optional[bool]
    cache_score: Optional[float]
    cache_coarse_score: Optional[float]
    cache_verify_score: Optional[float]
    cache_decision: Optional[str]
    cache_seed_phrases: List[str]
    cached_response: Optional[str]
