"""CacheProfile registry — slug defaults + node overrides (H21 / CACHE_PROFILES.md)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from chorusgraph.sections.models import CacheProfile

_DEFAULT_PATH = Path(__file__).with_name("profiles.default.json")


@lru_cache(maxsize=1)
def load_default_profiles(path: Optional[str] = None) -> Dict[str, CacheProfile]:
    p = Path(path) if path else _DEFAULT_PATH
    raw = json.loads(p.read_text(encoding="utf-8"))
    return {slug: CacheProfile.model_validate(cfg) for slug, cfg in raw.items()}


class ProfileRegistry:
    """Resolve CacheProfile for category_slug with optional per-node override."""

    def __init__(self, profiles: Optional[Dict[str, CacheProfile]] = None) -> None:
        self._profiles = dict(profiles or load_default_profiles())

    def register(self, slug: str, profile: CacheProfile) -> None:
        self._profiles[slug] = profile

    def get(self, category_slug: str, *, override: Optional[CacheProfile] = None) -> CacheProfile:
        if override is not None:
            return override
        if category_slug in self._profiles:
            return self._profiles[category_slug]
        return self._profiles.get("general", CacheProfile())

    def slugs(self) -> frozenset[str]:
        return frozenset(self._profiles)


def default_registry() -> ProfileRegistry:
    return ProfileRegistry()


__all__ = ["ProfileRegistry", "default_registry", "load_default_profiles"]
