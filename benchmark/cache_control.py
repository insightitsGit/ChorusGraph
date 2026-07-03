"""Disable semantic cache for honest cold-path benchmarks (0% cache hit rate)."""

from __future__ import annotations

from typing import Any, Dict

from benchmark.benchmark_flags import get_flags

_INSTALLED = False


def cache_benchmark_enabled() -> bool:
    return get_flags().cache_enabled


def forced_cache_miss_state() -> Dict[str, Any]:
    return {
        "cache_hit": False,
        "cache_score": None,
        "cache_coarse_score": None,
        "cache_verify_score": None,
        "cache_decision": "benchmark_disabled",
    }


def install_benchmark_cache_policy() -> None:
    """
    Wrap gate/seed so ``configure(cache_enabled=False)`` forces misses and no seeding.

    Safe to call once per process; checks flags on every gate/seed invocation.
    """
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    import importlib

    import chorusgraph.cache_gate as cache_gate_pkg

    gate_mod = importlib.import_module("chorusgraph.cache_gate.gate")
    backend_mod = importlib.import_module("chorusgraph.cache_gate.backend")
    from chorusgraph.cache_gate.decision import Decision, DecisionKind

    _orig_gate = gate_mod.gate
    _orig_seed = backend_mod.seed_cache_entry

    def gate_benchmark(*args: Any, **kwargs: Any) -> Decision:
        if cache_benchmark_enabled():
            return _orig_gate(*args, **kwargs)
        return Decision(kind=DecisionKind.MISS, coarse_score=0.0)

    def seed_benchmark(*args: Any, **kwargs: Any) -> None:
        if cache_benchmark_enabled():
            _orig_seed(*args, **kwargs)

    gate_mod.gate = gate_benchmark  # type: ignore[assignment]
    cache_gate_pkg.gate = gate_benchmark  # re-export used by finance nodes
    backend_mod.seed_cache_entry = seed_benchmark  # type: ignore[assignment]
    cache_gate_pkg.seed_cache_entry = seed_benchmark

    if not cache_benchmark_enabled():
        try:
            from benchmark.hc2 import runner as hc2_runner

            hc2_runner.HC2Runner._shared_runtime = None
        except ImportError:
            pass


def reset_benchmark_cache_policy() -> None:
    """Test helper — allow re-install in isolated tests."""
    global _INSTALLED
    _INSTALLED = False


__all__ = [
    "cache_benchmark_enabled",
    "forced_cache_miss_state",
    "install_benchmark_cache_policy",
    "reset_benchmark_cache_policy",
]
