"""Idempotency guard for retried side effects (E2)."""

from __future__ import annotations

import threading
from typing import Set


class IdempotencyGuard:
    """In-process dedup for operations that must not double-apply on retry."""

    def __init__(self) -> None:
        self._seen: Set[str] = set()
        self._lock = threading.Lock()

    def try_acquire(self, key: str) -> bool:
        with self._lock:
            if key in self._seen:
                return False
            self._seen.add(key)
            return True

    def release(self, key: str) -> None:
        with self._lock:
            self._seen.discard(key)

    def clear(self) -> None:
        with self._lock:
            self._seen.clear()
