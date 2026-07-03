"""Process-wide benchmark toggles (set once per ``run_scenarios`` invocation)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BenchmarkFlags:
    """Honest-benchmark defaults: cache on (production-like). Use ``--no-cache`` for cold-path only."""

    cache_enabled: bool = True


_flags = BenchmarkFlags()


def get_flags() -> BenchmarkFlags:
    return _flags


def configure(*, cache_enabled: bool | None = None) -> BenchmarkFlags:
    if cache_enabled is not None:
        _flags.cache_enabled = cache_enabled
    return _flags


def reset_flags() -> None:
    global _flags
    _flags = BenchmarkFlags()


__all__ = ["BenchmarkFlags", "configure", "get_flags", "reset_flags"]
