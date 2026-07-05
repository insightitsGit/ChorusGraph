"""Tests for two-stage cache gate."""

from __future__ import annotations

import pytest
from prism.cache.embedder import HashEmbedder

from chorusgraph.cache_gate import SidecarStore, gate, seed_cache_entry
from chorusgraph.cache_gate.decision import DecisionKind
from chorusgraph.ledger.instrument import make_cache_gate_step
from chorusgraph.policy.embedder_guard import (
    assert_semantic_embedder,
    build_guarded_cache,
    is_hash_embedder,
)
from chorusgraph.sections.models import CachePolicy, Section


def _section(slug: str = "greeting", policy: CachePolicy = CachePolicy.EXACT) -> Section:
    return Section(
        section_id="test",
        category_slug=slug,
        content="hello there",
        cache_policy=policy,
    )


def test_gate_miss_when_cache_empty():
    cache = build_guarded_cache("gate-test-empty")
    sidecar = SidecarStore(":memory:")
    decision = gate("hello", _section(), cache, sidecar, verify_threshold=0.95)
    assert decision.kind == DecisionKind.MISS


def test_gate_hit_on_paraphrase_after_seed():
    cache = build_guarded_cache("gate-test-hit")
    sidecar = SidecarStore(":memory:")
    value = {"route": "greeting"}
    seed_cache_entry(
        cache,
        sidecar,
        query="hello there",
        value=value,
        category_slug="greeting",
        cache_policy="exact",
    )
    decision = gate(
        "hello there",
        _section(),
        cache,
        sidecar,
        coarse_threshold=0.88,
        verify_threshold=0.95,
    )
    assert decision.is_hit
    assert decision.kind == DecisionKind.HIT_REUSE
    assert decision.value == value
    assert decision.verify_score > 0.0


def test_gate_miss_on_cross_category_slug():
    cache = build_guarded_cache("gate-test-taxonomy")
    sidecar = SidecarStore(":memory:")
    seed_cache_entry(
        cache,
        sidecar,
        query="hello there",
        value={"route": "greeting"},
        category_slug="greeting",
        cache_policy="exact",
    )
    section = Section(
        section_id="pricing",
        category_slug="pricing",
        content="how much",
        cache_policy=CachePolicy.EXACT,
    )
    decision = gate(
        "hi",
        section,
        cache,
        sidecar,
        coarse_threshold=0.80,
        verify_threshold=0.85,
    )
    assert decision.kind == DecisionKind.MISS


def test_semantic_policy_returns_hit_as_context():
    cache = build_guarded_cache("gate-test-semantic")
    sidecar = SidecarStore(":memory:")
    seed_cache_entry(
        cache,
        sidecar,
        query="how does agentic rag work",
        value={"draft": "RAG flow"},
        category_slug="general",
        cache_policy="semantic",
    )
    section = Section(
        section_id="general",
        category_slug="general",
        content="explain agentic rag",
        cache_policy=CachePolicy.SEMANTIC,
    )
    decision = gate(
        "explain agentic rag flow",
        section,
        cache,
        sidecar,
        coarse_threshold=0.75,
        verify_threshold=0.80,
    )
    if decision.is_hit:
        assert decision.kind == DecisionKind.HIT_AS_CONTEXT
        assert not decision.counts_for_fp


def test_ledger_cache_fields_populated():
    cache = build_guarded_cache("gate-test-ledger")
    sidecar = SidecarStore(":memory:")
    seed_cache_entry(
        cache,
        sidecar,
        query="hello there",
        value={"route": "greeting"},
        category_slug="greeting",
        cache_policy="exact",
    )
    decision = gate(
        "hello",
        _section(),
        cache,
        sidecar,
        coarse_threshold=0.82,
        verify_threshold=0.75,
    )
    step = make_cache_gate_step("cache_gate", decision)
    assert step.cache_hit is not None
    assert step.cache_score is not None
    if decision.is_hit:
        assert step.cache_hit is True


def test_embedder_guard_blocks_hash_embedder():
    with pytest.raises(RuntimeError, match="HashEmbedder"):
        assert_semantic_embedder(HashEmbedder())


def test_embedder_guard_accepts_prismlang_onnx():
    from chorusgraph.embedders import PrismlangOnnxEmbedder

    assert_semantic_embedder(PrismlangOnnxEmbedder())
    assert not is_hash_embedder(PrismlangOnnxEmbedder())
