"""Route → cache policy mapping for hub replay."""

from __future__ import annotations

from chorusgraph.sections.models import CachePolicy

# Hub `route` column maps to category_slug in export SQL.
ROUTE_TO_POLICY: dict[str, CachePolicy] = {
    "greeting": CachePolicy.EXACT,
    "site_kb": CachePolicy.REPLAY_SAFE,
    "needs_web": CachePolicy.REPLAY_SAFE,
    "general": CachePolicy.SEMANTIC,
    "none": CachePolicy.NO_CACHE,
}


def policy_for_slug(slug: str) -> CachePolicy:
    return ROUTE_TO_POLICY.get(slug or "general", CachePolicy.SEMANTIC)
