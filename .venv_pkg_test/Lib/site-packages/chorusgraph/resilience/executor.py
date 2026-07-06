"""Unified resilient executor — timeout, retry, circuit breaker (E2)."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Callable, TypeVar

from chorusgraph.resilience.circuit_breaker import get_breaker
from chorusgraph.resilience.errors import ChorusExternalError, ErrorKind, ExternalError, classify_exception
from chorusgraph.resilience.policy import CallPolicy

T = TypeVar("T")

_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="resilience")


def resilient_call(
    service: str,
    fn: Callable[[], T],
    *,
    policy: CallPolicy | None = None,
) -> T:
    """
    Execute ``fn`` with bounded retries, exponential backoff, and a per-service breaker.

    Raises ``ChorusExternalError`` when retries are exhausted or the breaker is open.
    """
    policy = policy or CallPolicy()
    breaker = get_breaker(service, policy.breaker)
    last_error: ExternalError | None = None
    max_attempts = policy.retry.max_retries + 1

    for attempt in range(1, max_attempts + 1):
        breaker.before_call()
        try:
            future = _EXECUTOR.submit(fn)
            result = future.result(timeout=policy.timeout_seconds)
            breaker.record_success()
            return result
        except FuturesTimeout:
            last_error = ExternalError(
                service, "timeout", f"exceeded {policy.timeout_seconds}s", ErrorKind.TRANSIENT, True, attempt
            )
            breaker.record_failure()
        except ChorusExternalError as exc:
            d = exc.detail
            last_error = ExternalError(d.service, d.code, d.message, d.kind, d.retryable, attempt)
            breaker.record_failure()
            if not last_error.retryable:
                raise
        except Exception as exc:
            last_error = classify_exception(exc, service=service)
            last_error = ExternalError(
                last_error.service,
                last_error.code,
                last_error.message,
                last_error.kind,
                last_error.retryable,
                attempt,
            )
            breaker.record_failure()
            if not last_error.retryable:
                raise ChorusExternalError(last_error) from exc

        if attempt >= max_attempts or last_error is None or not last_error.retryable:
            break
        time.sleep(policy.retry.delay_for_attempt(attempt))

    assert last_error is not None
    raise ChorusExternalError(last_error)
