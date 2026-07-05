"""Typed error taxonomy for external calls and node failures (E2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ErrorKind(str, Enum):
    """Transient errors may retry; permanent errors must not."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"


@dataclass(frozen=True)
class ExternalError:
    """Structured failure from an external dependency."""

    service: str
    code: str
    message: str
    kind: ErrorKind
    retryable: bool
    attempts: int = 1

    @property
    def ledger_rule(self) -> str:
        return f"error:{self.code}:{self.kind.value}"


class ChorusExternalError(Exception):
    """Raised when resilient_call exhausts retries or the breaker is open."""

    def __init__(self, detail: ExternalError) -> None:
        self.detail = detail
        super().__init__(f"[{detail.service}] {detail.code}: {detail.message}")


def classify_exception(exc: Exception, *, service: str) -> ExternalError:
    """Map arbitrary exceptions to the E2 taxonomy."""
    import httpx

    name = type(exc).__name__
    msg = str(exc) or name

    if isinstance(exc, ChorusExternalError):
        return exc.detail

    if isinstance(exc, (TimeoutError, httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout)):
        return ExternalError(service, "timeout", msg, ErrorKind.TRANSIENT, True)

    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (408, 429, 500, 502, 503, 504):
            return ExternalError(service, f"http_{status}", msg, ErrorKind.TRANSIENT, True)
        return ExternalError(service, f"http_{status}", msg, ErrorKind.PERMANENT, False)

    if isinstance(exc, (httpx.NetworkError, ConnectionError, OSError)):
        return ExternalError(service, "network", msg, ErrorKind.TRANSIENT, True)

    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return ExternalError(service, "invalid_input", msg, ErrorKind.PERMANENT, False)

    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        return ExternalError(service, "rate_limit", msg, ErrorKind.TRANSIENT, True)

    if "401" in msg or "403" in msg or "API key" in msg:
        return ExternalError(service, "auth", msg, ErrorKind.PERMANENT, False)

    return ExternalError(service, name.lower(), msg, ErrorKind.TRANSIENT, True)
