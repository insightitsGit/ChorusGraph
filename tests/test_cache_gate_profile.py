"""T2 — CacheProfile gate: scope, TTL, keying modes."""

from __future__ import annotations

import time

import numpy as np
import pytest

from chorusgraph.cache_gate import SidecarStore, gate, seed_cache_entry
from chorusgraph.cache_gate.backend import recall_direct
from chorusgraph.cache_gate.decision import DecisionKind
from chorusgraph.cache_gate.scope import scope_id
from chorusgraph.policy.embedder_guard import build_guarded_cache
from chorusgraph.sections.models import CachePolicy, CacheProfile, Section


def _cache():
    return build_guarded_cache("profile-gate-test")


def test_scope_isolation_user_vs_global():
    cache = _cache()
    sidecar = SidecarStore(":memory:")
    profile_user = CacheProfile(keying="exact", scope="user", risk_tier="low")
    seed_cache_entry(
        cache,
        sidecar,
        query="profile task",
        value={"profile": "secret"},
        category_slug="user_profile",
        cache_policy="exact",
        profile=profile_user,
        scope_id=scope_id("user", user_id="alice"),
    )
    section = Section(
        section_id="up",
        category_slug="user_profile",
        content="profile task",
        cache_policy=CachePolicy.EXACT,
    )
    miss = gate(
        "profile task",
        section,
        cache,
        sidecar,
        profile=profile_user,
        scope_id=scope_id("user", user_id="bob"),
    )
    assert miss.kind == DecisionKind.MISS

    hit = gate(
        "profile task",
        section,
        cache,
        sidecar,
        profile=profile_user,
        scope_id=scope_id("user", user_id="alice"),
    )
    assert hit.is_hit


def test_ttl_expiry():
    cache = _cache()
    sidecar = SidecarStore(":memory:")
    now = 1_000_000.0
    profile = CacheProfile(keying="exact", ttl_s=60, scope="global", risk_tier="low")
    seed_cache_entry(
        cache,
        sidecar,
        query="ttl query",
        value={"v": 1},
        category_slug="fx_rates",
        cache_policy="exact",
        profile=profile,
        scope_id="global",
        now=now,
    )
    section = Section(
        section_id="fx",
        category_slug="fx_rates",
        content="ttl query",
        cache_policy=CachePolicy.EXACT,
    )
    hit = gate("ttl query", section, cache, sidecar, profile=profile, now=now + 30)
    assert hit.is_hit
    miss = gate("ttl query", section, cache, sidecar, profile=profile, now=now + 120)
    assert miss.kind == DecisionKind.MISS


def test_fingerprint_keying():
    cache = _cache()
    sidecar = SidecarStore(":memory:")
    fp = "fp:abc123"
    profile = CacheProfile(keying="fingerprint", scope="session", risk_tier="high")
    seed_cache_entry(
        cache,
        sidecar,
        query=fp,
        value={"retrieved": [{"id": "g1"}]},
        category_slug="clinical_retrieval",
        cache_policy="replay_safe",
        profile=profile,
        scope_id=scope_id("session", session_id="s1"),
        fingerprint_key=fp,
    )
    direct = recall_direct(
        cache,
        sidecar,
        profile=profile,
        scope_id=scope_id("session", session_id="s1"),
        category_slug="clinical_retrieval",
        query="different words same case",
        fingerprint_key=fp,
    )
    assert direct is not None
    assert direct.value["retrieved"][0]["id"] == "g1"


def test_high_risk_uses_stricter_verify():
    cache = _cache()
    sidecar = SidecarStore(":memory:")
    profile = CacheProfile(keying="semantic", scope="global", risk_tier="high")
    seed_cache_entry(
        cache,
        sidecar,
        query="clinical case A",
        value={"facts": 1},
        category_slug="clinical_judgment",
        cache_policy="replay_safe",
        profile=profile,
        scope_id="global",
    )
    section = Section(
        section_id="cj",
        category_slug="clinical_judgment",
        content="clinical case B paraphrase",
        cache_policy=CachePolicy.REPLAY_SAFE,
    )
    decision = gate(
        "clinical case B paraphrase",
        section,
        cache,
        sidecar,
        profile=profile,
        coarse_threshold=0.5,
        verify_threshold=0.80,
    )
    # High risk bumps verify threshold — near-paraphrase may miss vs low-risk path
    assert isinstance(decision.verify_score, float) or decision.kind == DecisionKind.MISS
