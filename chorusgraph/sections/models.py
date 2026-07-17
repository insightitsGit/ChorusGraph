"""Pydantic section model — cache policy boundary for ChorusGraph."""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class CachePolicy(str, Enum):
    NO_CACHE = "no_cache"
    SEMANTIC = "semantic"
    EXACT = "exact"
    REPLAY_SAFE = "replay_safe"


CacheKeying = Literal["semantic", "fingerprint", "exact"]
CacheScope = Literal["global", "tenant", "user", "session"]
RiskTier = Literal["low", "high"]


class CacheProfile(BaseModel):
    """
    Measured cache attributes per category_slug (CACHE_PROFILES.md §3).

    Attach per node via NodeCacheSpec.profile override.
    """

    keying: CacheKeying = "semantic"
    ttl_s: Optional[int] = None
    scope: CacheScope = "global"
    risk_tier: RiskTier = "low"
    # ADR-006 — opt-in L1 single-flight; ignored unless keying/scope allow.
    single_flight: bool = False
    single_flight_timeout_s: Optional[float] = None


class Section(BaseModel):
    """Declarative state section with taxonomy and cache policy."""

    section_id: str
    category_slug: str
    content: Any = None
    vector: Optional[List[float]] = Field(
        default=None,
        description="64-d projected vector (computed once per update)",
    )
    cache_policy: CachePolicy = CachePolicy.NO_CACHE
