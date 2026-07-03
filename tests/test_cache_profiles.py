"""T1 — CacheProfile schema and registry tests."""

from __future__ import annotations

import pytest

from chorusgraph.core.cache_interceptor import NodeCacheSpec
from chorusgraph.sections.models import CachePolicy, CacheProfile
from chorusgraph.sections.profiles import ProfileRegistry, load_default_profiles


def test_default_registry_has_fx_and_clinical():
    profiles = load_default_profiles()
    assert "fx_rates" in profiles
    assert profiles["fx_rates"].keying == "semantic"
    assert profiles["fx_rates"].scope == "global"
    assert profiles["clinical_judgment"].keying == "fingerprint"
    assert profiles["clinical_judgment"].risk_tier == "high"


def test_registry_node_override():
    reg = ProfileRegistry()
    override = CacheProfile(keying="exact", scope="session", risk_tier="high")
    got = reg.get("fx_rates", override=override)
    assert got.keying == "exact"
    assert got.scope == "session"


def test_node_cache_spec_accepts_profile():
    spec = NodeCacheSpec(
        node_id="cache_gate",
        category_slug="clinical_retrieval",
        cache_policy=CachePolicy.REPLAY_SAFE,
        profile=CacheProfile(scope="global"),
    )
    assert spec.profile.scope == "global"
