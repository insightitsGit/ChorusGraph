"""Retry and call policies for resilient external I/O (E2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from chorusgraph.resilience.circuit_breaker import BreakerConfig


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 2
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 4.0
    exponential_base: float = 2.0

    def delay_for_attempt(self, attempt: int) -> float:
        delay = self.base_delay_seconds * (self.exponential_base ** (attempt - 1))
        return min(delay, self.max_delay_seconds)


@dataclass(frozen=True)
class CallPolicy:
    timeout_seconds: float = 30.0
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    breaker: BreakerConfig = field(default_factory=BreakerConfig)

    @classmethod
    def tool(cls) -> "CallPolicy":
        return cls(timeout_seconds=12.0, retry=RetryPolicy(max_retries=2))

    @classmethod
    def llm(cls) -> "CallPolicy":
        return cls(timeout_seconds=60.0, retry=RetryPolicy(max_retries=2, base_delay_seconds=0.5))

    @classmethod
    def db(cls) -> "CallPolicy":
        return cls(timeout_seconds=10.0, retry=RetryPolicy(max_retries=1))

    @classmethod
    def cortex(cls) -> "CallPolicy":
        return cls(timeout_seconds=30.0, retry=RetryPolicy(max_retries=1))
