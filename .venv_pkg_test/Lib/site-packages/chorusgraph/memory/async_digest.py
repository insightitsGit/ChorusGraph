"""Background digest/sleep scheduler — keeps memory writes off the response path."""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, List

from chorusgraph.resilience.idempotency import IdempotencyGuard

logger = logging.getLogger(__name__)

_SHARED_GUARD = IdempotencyGuard()


class AsyncDigester:
    """Fire-and-forget digest + idle sleep on a background thread pool."""

    def __init__(
        self,
        memory_factory: Callable[[], Any],
        *,
        idempotency: IdempotencyGuard | None = None,
    ) -> None:
        self._memory_factory = memory_factory
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cortex-digest")
        self._futures: List[Future] = []
        self._idempotency = idempotency or _SHARED_GUARD

    def submit_digest(self, text: str, *, source_id: str, agent_id: str) -> Future:
        future = self._executor.submit(self._run_digest, text, source_id, agent_id)
        self._futures.append(future)
        return future

    def submit_sleep(self) -> Future:
        future = self._executor.submit(self._run_sleep)
        self._futures.append(future)
        return future

    def _run_digest(self, text: str, source_id: str, agent_id: str) -> str:
        from prismcortex.models import DigestOutcome

        key = f"digest:{source_id}"
        if not self._idempotency.try_acquire(key):
            logger.debug("cortex digest skipped duplicate source_id=%s", source_id)
            return "skipped_duplicate"

        mem = self._memory_factory()
        try:
            result = mem.digest(text, source_id=source_id, agent_id=agent_id)
        except Exception as exc:
            logger.warning("cortex digest failed for %s: %s", source_id, exc)
            return "failed"
        logger.debug("cortex digest outcome=%s reason=%s", result.outcome, result.reason)
        if result.outcome == DigestOutcome.STAGED:
            try:
                mem.sleep()
            except Exception as exc:
                logger.warning("cortex sleep failed after digest %s: %s", source_id, exc)
        return result.outcome.value

    def _run_sleep(self) -> int:
        mem = self._memory_factory()
        try:
            return mem.sleep()
        except Exception as exc:
            logger.warning("cortex sleep failed: %s", exc)
            return 0

    def wait_idle(self, timeout: float = 120.0) -> None:
        pending = list(self._futures)
        self._futures.clear()
        for future in pending:
            try:
                future.result(timeout=timeout)
            except Exception as exc:
                logger.warning("cortex background task failed: %s", exc)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
