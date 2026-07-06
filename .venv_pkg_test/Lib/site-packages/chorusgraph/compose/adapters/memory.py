"""PrismCortex memory adapter."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from chorusgraph.memory.cortex_service import CortexMemoryService, get_cortex_service


class CortexMemoryBackend:
    """Wraps ``CortexMemoryService`` as a ``MemoryBackend`` port."""

    name = "prism_cortex"

    def __init__(self, service: CortexMemoryService) -> None:
        self._service = service

    @property
    def service(self) -> CortexMemoryService:
        return self._service

    def schedule_digest(self, payload: str, *, source_id: str) -> None:
        self._service.schedule_digest(payload, source_id=source_id)

    def recall_structured(
        self,
        query: str,
        *,
        cache: Any = None,
        raw_384: Optional[np.ndarray] = None,
    ) -> Any:
        return self._service.recall_structured(query, cache=cache, raw_384=raw_384)


def default_memory_backend(
    *,
    tenant_id: str,
    cache_dir: str = ".chorusgraph/cortex",
) -> CortexMemoryBackend:
    return CortexMemoryBackend(
        get_cortex_service(tenant_id=tenant_id, cache_dir=cache_dir),
    )


__all__ = ["CortexMemoryBackend", "default_memory_backend"]
