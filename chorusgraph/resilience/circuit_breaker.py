"""Lightweight circuit breaker registry (E2)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict

from chorusgraph.resilience.errors import ChorusExternalError, ErrorKind, ExternalError


@dataclass
class BreakerConfig:
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    half_open_max_calls: int = 1


@dataclass
class _BreakerState:
    config: BreakerConfig
    failures: int = 0
    opened_at: float | None = None
    half_open_calls: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)


class CircuitBreaker:
    """Per-service breaker — opens after consecutive failures, half-opens after cooldown."""

    def __init__(self, service: str, config: BreakerConfig | None = None) -> None:
        self.service = service
        self._state = _BreakerState(config or BreakerConfig())

    def _is_open(self) -> bool:
        st = self._state
        if st.opened_at is None:
            return False
        elapsed = time.monotonic() - st.opened_at
        if elapsed >= st.config.recovery_timeout_seconds:
            st.half_open_calls = 0
            return False
        return True

    def before_call(self) -> None:
        with self._state.lock:
            st = self._state
            if st.opened_at is None:
                return
            elapsed = time.monotonic() - st.opened_at
            if elapsed < st.config.recovery_timeout_seconds:
                raise ChorusExternalError(
                    ExternalError(
                        self.service,
                        "circuit_open",
                        "circuit breaker open — fast-fail",
                        ErrorKind.TRANSIENT,
                        True,
                    )
                )
            if st.half_open_calls >= st.config.half_open_max_calls:
                raise ChorusExternalError(
                    ExternalError(
                        self.service,
                        "circuit_open",
                        "circuit breaker half-open — probe limit reached",
                        ErrorKind.TRANSIENT,
                        True,
                    )
                )
            st.half_open_calls += 1

    def record_success(self) -> None:
        with self._state.lock:
            self._state.failures = 0
            self._state.opened_at = None
            self._state.half_open_calls = 0

    def record_failure(self) -> None:
        with self._state.lock:
            self._state.failures += 1
            if self._state.failures >= self._state.config.failure_threshold:
                self._state.opened_at = time.monotonic()
                self._state.half_open_calls = 0


_REGISTRY: Dict[str, CircuitBreaker] = {}
_REGISTRY_LOCK = threading.Lock()


def get_breaker(service: str, config: BreakerConfig | None = None) -> CircuitBreaker:
    with _REGISTRY_LOCK:
        breaker = _REGISTRY.get(service)
        if breaker is None:
            breaker = CircuitBreaker(service, config)
            _REGISTRY[service] = breaker
        return breaker


def reset_breakers() -> None:
    """Test helper — clear breaker registry."""
    with _REGISTRY_LOCK:
        _REGISTRY.clear()
