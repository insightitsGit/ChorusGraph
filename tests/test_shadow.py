"""Tests for shadow-mode measurement harness."""

from __future__ import annotations

from chorusgraph.sections.models import CachePolicy
from chorusgraph.shadow.harness import run_shadow_measurement
from chorusgraph.shadow.report import FP_BUDGET, recommend_threshold


def test_shadow_measurement_produces_frontier():
    result = run_shadow_measurement()
    assert len(result.rows) > 0
    assert len(result.frontier) > 0
    assert "LOCAL PROXY" in result.report
    assert any(p.n_queries > 0 for p in result.frontier)


def test_ledger_cache_hit_populated_in_shadow():
    result = run_shadow_measurement()
    cache_steps = [s for s in result.ledger.steps if s.node == "cache_gate"]
    assert len(cache_steps) > 0
    assert all(s.cache_hit is not None for s in cache_steps)
    assert all(s.cache_score is not None for s in cache_steps)


def test_dataset_has_semantic_and_exact_policies():
    result = run_shadow_measurement()
    policies = {r.cache_policy for r in result.rows}
    assert CachePolicy.EXACT.value in policies
    assert CachePolicy.REPLAY_SAFE.value in policies
    assert CachePolicy.SEMANTIC.value in policies


def test_recommend_threshold_helper():
    result = run_shadow_measurement()
    rec = recommend_threshold(result.frontier)
    for slug, thresh in rec.items():
        matching = [p for p in result.frontier if p.slug == slug and p.verify_threshold == thresh]
        assert matching
        assert matching[0].false_positive_rate < FP_BUDGET
