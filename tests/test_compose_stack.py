"""Tests for ChorusStack composable product wiring."""

from __future__ import annotations

from chorusgraph.cache_gate import gate, seed_cache_entry
from chorusgraph.compose import ChorusStack, PrismCacheBackend, RedisCacheBackend
from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import dict_node_adapter
from chorusgraph.sections.models import CachePolicy, CacheProfile, Section


def test_chorus_stack_defaults_resolve_full_product():
    stack = ChorusStack.defaults(tenant_id="compose-test")
    cache = stack.resolve_cache()
    assert isinstance(cache, PrismCacheBackend)
    assert cache.name == "prism"
    assert stack.resolve_sidecar() is not None
    assert stack.resolve_checkpointer() is not None
    assert stack.resolve_ledger() is not None
    assert stack.resolve_tools() is not None


def test_chorus_stack_disable_memory():
    stack = ChorusStack.defaults(tenant_id="t", enable_memory=False)
    assert stack.resolve_memory() is None


def test_graph_compile_attaches_stack():
    g = Graph(tenant_id="t", graph_id="compose")
    g.add_node("n", dict_node_adapter(lambda s: {"ok": True}, hop="n"))
    g.add_edge(START, "n")
    g.add_edge("n", END)
    compiled = g.compile()
    assert compiled.stack is not None
    assert compiled.stack.tenant_id == "t"
    assert compiled.checkpointer is None


def test_redis_cache_backend_exact_hit():
    backend = RedisCacheBackend(tenant_id="redis-test")
    section = Section(
        section_id="s1",
        category_slug="fx_rates",
        content="hello",
        cache_policy=CachePolicy.REPLAY_SAFE,
    )
    profile = CacheProfile(keying="exact")
    seed_cache_entry(
        backend,
        None,
        query="What is USD/EUR?",
        value={"rate": 0.9},
        category_slug="fx_rates",
        cache_policy="replay_safe",
        profile=profile,
    )
    decision = gate(
        "What is USD/EUR?",
        section,
        backend,
        profile=profile,
        coarse_threshold=0.5,
        verify_threshold=0.5,
    )
    assert decision.is_hit
    assert decision.value == {"rate": 0.9}


def test_stack_with_cache_swap():
    redis = RedisCacheBackend(tenant_id="swap-test")
    stack = ChorusStack.defaults(tenant_id="swap-test").with_cache(redis)
    assert stack.resolve_cache().name == "redis"


def test_finance_runtime_uses_stack():
    from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

    rt = FinanceRuntime(tenant_id="fr", enable_cortex=False)
    assert rt.stack is not None
    assert isinstance(rt.cache_backend, PrismCacheBackend)
