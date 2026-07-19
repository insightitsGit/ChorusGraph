"""Sidecar must_revalidate + Decision.force_refresh (PrismShine consistency)."""

from __future__ import annotations

from chorusgraph.cache_gate import SidecarStore, gate, mark_revalidate, seed_cache_entry
from chorusgraph.cache_gate.decision import DecisionKind
from chorusgraph.core.cache_interceptor import CacheInterceptor, CacheRuntime, NodeCacheSpec
from chorusgraph.ledger.instrument import make_cache_gate_step
from chorusgraph.policy.embedder_guard import build_guarded_cache
from chorusgraph.sections.models import CachePolicy, CacheProfile, Section


def _section(
    slug: str = "greeting",
    policy: CachePolicy = CachePolicy.EXACT,
) -> Section:
    return Section(
        section_id="test",
        category_slug=slug,
        content="hello there",
        cache_policy=policy,
    )


def test_mark_revalidate_sets_force_refresh_once():
    cache = build_guarded_cache("reval-force")
    sidecar = SidecarStore(":memory:")
    seed_cache_entry(
        cache,
        sidecar,
        query="hello there",
        value={"route": "greeting"},
        category_slug="greeting",
        cache_policy="exact",
    )
    hit = gate(
        "hello there",
        _section(),
        cache,
        sidecar,
        coarse_threshold=0.88,
        verify_threshold=0.95,
    )
    assert hit.is_hit
    assert hit.force_refresh is False
    assert hit.created_at is not None
    # prismlib-plus ≥0.8.0: store entry created_at preferred when present
    store_entry = cache._store.load(hit.candidate_packet_id)
    if store_entry is not None and getattr(store_entry, "created_at", None) is not None:
        assert hit.created_at == float(store_entry.created_at)
    assert hit.candidate_packet_id

    n = mark_revalidate(sidecar, packet_ids=[hit.candidate_packet_id])
    assert n == 1

    forced = gate(
        "hello there",
        _section(),
        cache,
        sidecar,
        coarse_threshold=0.88,
        verify_threshold=0.95,
    )
    assert forced.is_hit
    assert forced.force_refresh is True
    assert forced.kind == DecisionKind.HIT_REVALIDATE
    step = make_cache_gate_step("cache_gate", forced)
    assert step.detail is not None
    assert step.detail.get("force_refresh") is True
    assert step.detail.get("created_at") == forced.created_at

    # Re-seed clears must_revalidate (INSERT OR REPLACE … must_revalidate=0).
    seed_cache_entry(
        cache,
        sidecar,
        query="hello there",
        value={"route": "greeting", "v": 2},
        category_slug="greeting",
        cache_policy="exact",
    )
    after = gate(
        "hello there",
        _section(),
        cache,
        sidecar,
        coarse_threshold=0.88,
        verify_threshold=0.95,
    )
    assert after.is_hit
    assert after.force_refresh is False


def test_replay_safe_still_skips_without_mark():
    """REPLAY_SAFE labels HIT_REVALIDATE but does not force_refresh when bit unset."""
    cache = build_guarded_cache("reval-replay")
    sidecar = SidecarStore(":memory:")
    seed_cache_entry(
        cache,
        sidecar,
        query="hello there",
        value={"answer": "ok"},
        category_slug="greeting",
        cache_policy="replay_safe",
        profile=CacheProfile(keying="exact"),
    )
    decision = gate(
        "hello there",
        _section(policy=CachePolicy.REPLAY_SAFE),
        cache,
        sidecar,
        coarse_threshold=0.88,
        verify_threshold=0.95,
        profile=CacheProfile(keying="exact"),
    )
    assert decision.is_hit
    assert decision.kind == DecisionKind.HIT_REVALIDATE
    assert decision.force_refresh is False

    runtime = CacheRuntime(cache=cache, sidecar=sidecar, tenant_id="reval-replay")
    interceptor = CacheInterceptor(
        runtime,
        {
            "gen": NodeCacheSpec(
                node_id="gen",
                category_slug="greeting",
                cache_policy=CachePolicy.REPLAY_SAFE,
                profile=CacheProfile(keying="exact"),
            )
        },
    )
    skipped = interceptor.try_skip(
        "gen",
        {"message": "hello there"},
        super_step=1,
    )
    assert skipped is not None


def test_force_refresh_prevents_try_skip():
    cache = build_guarded_cache("reval-skip")
    sidecar = SidecarStore(":memory:")
    seed_cache_entry(
        cache,
        sidecar,
        query="hello there",
        value={"answer": "ok"},
        category_slug="greeting",
        cache_policy="exact",
    )
    hit = gate(
        "hello there",
        _section(),
        cache,
        sidecar,
        coarse_threshold=0.88,
        verify_threshold=0.95,
    )
    mark_revalidate(sidecar, packet_ids=[hit.candidate_packet_id])

    runtime = CacheRuntime(cache=cache, sidecar=sidecar, tenant_id="reval-skip")
    interceptor = CacheInterceptor(
        runtime,
        {
            "gen": NodeCacheSpec(
                node_id="gen",
                category_slug="greeting",
                cache_policy=CachePolicy.EXACT,
            )
        },
    )
    assert interceptor.try_skip("gen", {"message": "hello there"}, super_step=1) is None
