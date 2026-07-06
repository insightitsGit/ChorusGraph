"""Per-tenant resource limits and noisy-neighbor protection (E6)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict


class TenantQuotaExceeded(RuntimeError):
    """Raised when a tenant exceeds configured limits."""


@dataclass
class TenantLimits:
    max_requests_per_minute: int = 120
    max_concurrent: int = 16
    max_memory_entries: int = 10_000


@dataclass
class _TenantBucket:
    window_start: float = field(default_factory=time.monotonic)
    request_count: int = 0
    concurrent: int = 0


class TenantResourceLimiter:
    """In-process rate/concurrency limits per tenant."""

    def __init__(self, limits: TenantLimits | None = None) -> None:
        self._limits = limits or TenantLimits()
        self._buckets: Dict[str, _TenantBucket] = {}
        self._lock = threading.Lock()

    def _bucket(self, tenant_id: str) -> _TenantBucket:
        if tenant_id not in self._buckets:
            self._buckets[tenant_id] = _TenantBucket()
        return self._buckets[tenant_id]

    def acquire(self, tenant_id: str) -> None:
        with self._lock:
            b = self._bucket(tenant_id)
            now = time.monotonic()
            if now - b.window_start >= 60.0:
                b.window_start = now
                b.request_count = 0
            if b.request_count >= self._limits.max_requests_per_minute:
                raise TenantQuotaExceeded(f"Rate limit exceeded for tenant {tenant_id}")
            if b.concurrent >= self._limits.max_concurrent:
                raise TenantQuotaExceeded(f"Concurrency limit exceeded for tenant {tenant_id}")
            b.request_count += 1
            b.concurrent += 1

    def release(self, tenant_id: str) -> None:
        with self._lock:
            b = self._bucket(tenant_id)
            b.concurrent = max(0, b.concurrent - 1)
