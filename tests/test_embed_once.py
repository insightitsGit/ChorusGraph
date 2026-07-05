"""H12 — embed-once per finance turn (vector ingress)."""

from __future__ import annotations

from chorusgraph.cache_gate import seed_cache_entry
from chorusgraph.embedders import CountingEmbedder
from chorusgraph.examples.finance_agent.patterns_graph import (
    build_react_graph,
    pattern_initial_state,
)
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime


def _seed_fx(runtime: FinanceRuntime, query: str, rate: float = 0.87727) -> None:
    seed_cache_entry(
        runtime.cache,
        runtime.sidecar,
        query=query,
        value={
            "from_currency": "USD",
            "to_currency": "EUR",
            "rate": rate,
            "date": "2026-07-02",
            "source": "frankfurter.app",
        },
        category_slug="fx_rates",
        cache_policy="replay_safe",
    )


def test_finance_turn_embeds_once_on_cache_hit():
    """Ingress + cache_gate + writer must not re-embed the same message."""
    query = "What is the USD to EUR exchange rate today?"
    runtime = FinanceRuntime(tenant_id="embed-once-hit", cortex=None)
    _seed_fx(runtime, query)

    compiled, _ = build_react_graph(runtime)
    result = compiled.invoke(pattern_initial_state(query))

    embedder = runtime.cache._embedder
    assert isinstance(embedder, CountingEmbedder)
    assert embedder.turn_calls == 1, f"expected 1 embed/turn, got {embedder.turn_calls}"
    assert result.get("cache_hit") is True
    assert result.get("response")


def test_finance_turn_embeds_once_on_miss_writer_path():
    """Miss path: ingress + cache_gate + writer still only one ONNX embed."""
    query = "What is the USD to GBP exchange rate today?"
    runtime = FinanceRuntime(tenant_id="embed-once-miss", cortex=None)
    from chorusgraph.examples.finance_agent.nodes import (
        make_cache_gate_handler,
        make_vector_ingress_handler,
        make_writer_handler,
    )

    state = pattern_initial_state(
        query,
        tool_result={
            "from_currency": "USD",
            "to_currency": "GBP",
            "rate": 0.75151,
            "date": "2026-07-02",
        },
    )
    ingress = make_vector_ingress_handler(runtime)
    gate = make_cache_gate_handler(runtime)
    writer = make_writer_handler(runtime)
    s = {**state, **ingress(state)}
    s = {**s, **gate(s)}
    s = {**s, **writer(s)}

    embedder = runtime.cache._embedder
    assert isinstance(embedder, CountingEmbedder)
    assert embedder.turn_calls == 1
    assert "0.75151" in (s.get("draft_response") or "")
