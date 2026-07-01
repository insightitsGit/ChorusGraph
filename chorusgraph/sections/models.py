"""Pydantic section model — cache policy boundary for ChorusGraph."""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class CachePolicy(str, Enum):
    NO_CACHE = "no_cache"
    SEMANTIC = "semantic"
    EXACT = "exact"
    REPLAY_SAFE = "replay_safe"


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
