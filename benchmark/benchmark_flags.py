"""Process-wide benchmark toggles (set once per ``run_scenarios`` invocation)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BenchmarkFlags:
    """Honest-benchmark defaults: cache on (production-like). Use ``--no-cache`` for cold-path only.

    ``temperature`` defaults to 0.2 (matches the product example client) so normal runs stay
    production-like. Pre/post comparisons that need to attribute a delta to a code change — not to
    Gemini sampling — should pass ``--temperature 0.0``: two runs of byte-identical code at
    temperature=0.2 were observed to disagree on 36/40 answer texts (HL2 baseline swung 70%->60%
    with zero code changes), which makes small deltas on small subgroups unreadable as signal.
    """

    cache_enabled: bool = True
    temperature: float = 0.2


_flags = BenchmarkFlags()


def get_flags() -> BenchmarkFlags:
    return _flags


def configure(*, cache_enabled: bool | None = None, temperature: float | None = None) -> BenchmarkFlags:
    if cache_enabled is not None:
        _flags.cache_enabled = cache_enabled
    if temperature is not None:
        _flags.temperature = temperature
    return _flags


def reset_flags() -> None:
    global _flags
    _flags = BenchmarkFlags()


__all__ = ["BenchmarkFlags", "configure", "get_flags", "reset_flags"]
