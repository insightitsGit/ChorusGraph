"""E2 resilience — timeouts, retries, circuit breakers, typed partial failures."""

from chorusgraph.resilience.circuit_breaker import CircuitBreaker, get_breaker, reset_breakers
from chorusgraph.resilience.errors import ChorusExternalError, ErrorKind, ExternalError, classify_exception
from chorusgraph.resilience.executor import resilient_call
from chorusgraph.resilience.idempotency import IdempotencyGuard
from chorusgraph.resilience.partial import PartialRunResult
from chorusgraph.resilience.policy import CallPolicy, RetryPolicy

__all__ = [
    "CallPolicy",
    "ChorusExternalError",
    "CircuitBreaker",
    "ErrorKind",
    "ExternalError",
    "IdempotencyGuard",
    "PartialRunResult",
    "RetryPolicy",
    "classify_exception",
    "get_breaker",
    "reset_breakers",
    "resilient_call",
]
