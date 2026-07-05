"""Benchmark cache disable policy."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from benchmark.benchmark_flags import configure, reset_flags
from benchmark.cache_control import (
    cache_benchmark_enabled,
    forced_cache_miss_state,
    install_benchmark_cache_policy,
    reset_benchmark_cache_policy,
)
from chorusgraph.cache_gate.decision import DecisionKind


@pytest.fixture(autouse=True)
def _reset_benchmark_flags():
    reset_flags()
    reset_benchmark_cache_policy()
    yield
    reset_flags()
    reset_benchmark_cache_policy()


def test_forced_cache_miss_state_shape():
    state = forced_cache_miss_state()
    assert state["cache_hit"] is False
    assert state["cache_decision"] == "benchmark_disabled"


def test_install_disables_gate_and_seed():
    configure(cache_enabled=False)
    install_benchmark_cache_policy()

    import chorusgraph.cache_gate as cache_gate_pkg

    cache = MagicMock()
    sidecar = MagicMock()
    from chorusgraph.sections.models import CachePolicy, Section

    section = Section(
        section_id="x",
        category_slug="fx_rates",
        content="hello",
        cache_policy=CachePolicy.REPLAY_SAFE,
    )
    decision = cache_gate_pkg.gate("hello", section, cache, sidecar)
    assert decision.kind == DecisionKind.MISS
    assert not decision.is_hit

    cache_gate_pkg.seed_cache_entry(
        cache, sidecar, query="q", value={"a": 1}, category_slug="fx_rates"
    )
    # seed is a no-op when cache disabled — no exception, no store write


def test_install_noop_when_cache_enabled():
    configure(cache_enabled=True)
    install_benchmark_cache_policy()
    assert cache_benchmark_enabled() is True


def test_temperature_defaults_to_production_value():
    from benchmark.benchmark_flags import get_flags

    assert get_flags().temperature == 0.2


def test_configure_temperature_reaches_gemini_call_config():
    """Deterministic-comparison mode: --temperature 0.0 must reach the actual API call config."""
    configure(temperature=0.0)

    from tests.support.deterministic import real_instrumented_gemini_client

    RealClient = real_instrumented_gemini_client()
    client = RealClient.__new__(RealClient)
    client.usage = __import__(
        "benchmark.shared.instrumented_gemini", fromlist=["LlmUsage"]
    ).LlmUsage()
    inner = MagicMock()
    inner._build_prompt.return_value = "prompt"
    client._inner = inner
    client._client = MagicMock()
    client.model = "gemini-test"
    response = MagicMock()
    response.text = "ok"
    response.usage_metadata = None
    client._client.models.generate_content.return_value = response

    client.generate("system", "user")

    _, kwargs = client._client.models.generate_content.call_args
    assert kwargs["config"].temperature == 0.0
