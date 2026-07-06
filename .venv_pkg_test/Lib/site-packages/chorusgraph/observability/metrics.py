"""Runtime metrics counters (E4)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class RuntimeMetrics:
    """In-process counters — export via health endpoint or OTel collector."""

    llm_calls: int = 0
    tool_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    node_latency_ms: Dict[str, int] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def inc(self, name: str, value: int = 1) -> None:
        with self._lock:
            current = getattr(self, name, None)
            if isinstance(current, int):
                setattr(self, name, current + value)

    def record_node_latency(self, node: str, duration_ms: int) -> None:
        with self._lock:
            self.node_latency_ms[node] = self.node_latency_ms.get(node, 0) + duration_ms

    def snapshot(self) -> Dict[str, object]:
        with self._lock:
            total_cache = self.cache_hits + self.cache_misses
            hit_rate = (self.cache_hits / total_cache) if total_cache else 0.0
            return {
                "llm_calls": self.llm_calls,
                "tool_calls": self.tool_calls,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_rate": round(hit_rate, 4),
                "errors": self.errors,
                "node_latency_ms_total": dict(self.node_latency_ms),
            }


_GLOBAL = RuntimeMetrics()


def get_metrics() -> RuntimeMetrics:
    return _GLOBAL
