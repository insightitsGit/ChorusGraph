"""Background digest/sleep scheduler — keeps memory writes off the response path."""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, List

logger = logging.getLogger(__name__)


class AsyncDigester:
    """Fire-and-forget digest + idle sleep on a background thread pool."""

    def __init__(self, memory_factory: Callable[[], Any]) -> None:
        self._memory_factory = memory_factory
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cortex-digest")
        self._futures: List[Future] = []

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

        mem = self._memory_factory()
        result = mem.digest(text, source_id=source_id, agent_id=agent_id)
        logger.debug("cortex digest outcome=%s reason=%s", result.outcome, result.reason)
        if result.outcome == DigestOutcome.STAGED:
            mem.sleep()
        return result.outcome.value

    def _run_sleep(self) -> int:
        mem = self._memory_factory()
        return mem.sleep()

    def wait_idle(self, timeout: float = 120.0) -> None:
        pending = list(self._futures)
        self._futures.clear()
        for future in pending:
            future.result(timeout=timeout)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
