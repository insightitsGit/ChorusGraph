"""Concurrent load harness for throughput characterization (E7)."""

from __future__ import annotations

import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class LoadSample:
    ok: bool
    latency_ms: float
    error: Optional[str] = None


@dataclass
class LoadReport:
    concurrency: int
    total_requests: int
    duration_seconds: float
    throughput_rps: float
    success_rate: float
    latency_p50_ms: float
    latency_p95_ms: float
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "concurrency": self.concurrency,
            "total_requests": self.total_requests,
            "duration_seconds": round(self.duration_seconds, 3),
            "throughput_rps": round(self.throughput_rps, 2),
            "success_rate": round(self.success_rate, 4),
            "latency_p50_ms": round(self.latency_p50_ms, 2),
            "latency_p95_ms": round(self.latency_p95_ms, 2),
            "error_count": len(self.errors),
        }


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(min(len(ordered) - 1, max(0, round(pct / 100.0 * (len(ordered) - 1)))))
    return ordered[idx]


def run_load(
    fn: Callable[[], None],
    *,
    total_requests: int = 50,
    concurrency: int = 4,
) -> LoadReport:
    """Execute ``fn`` concurrently and return throughput/latency envelope."""
    samples: List[LoadSample] = []

    def _one() -> LoadSample:
        start = time.perf_counter()
        try:
            fn()
            ms = (time.perf_counter() - start) * 1000.0
            return LoadSample(ok=True, latency_ms=ms)
        except Exception as exc:
            ms = (time.perf_counter() - start) * 1000.0
            return LoadSample(ok=False, latency_ms=ms, error=str(exc))

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(_one) for _ in range(total_requests)]
        for fut in as_completed(futures):
            samples.append(fut.result())
    elapsed = time.perf_counter() - started

    ok_latencies = [s.latency_ms for s in samples if s.ok]
    errors = [s.error for s in samples if s.error]
    ok_count = len(ok_latencies)
    return LoadReport(
        concurrency=concurrency,
        total_requests=total_requests,
        duration_seconds=elapsed,
        throughput_rps=total_requests / elapsed if elapsed else 0.0,
        success_rate=ok_count / total_requests if total_requests else 0.0,
        latency_p50_ms=_percentile(ok_latencies, 50),
        latency_p95_ms=_percentile(ok_latencies, 95),
        errors=errors[:10],
    )


def run_sweep(
    fn: Callable[[], None],
    *,
    concurrencies: Optional[List[int]] = None,
    requests_per_level: int = 40,
) -> List[LoadReport]:
    levels = concurrencies or [1, 2, 4, 8]
    return [run_load(fn, total_requests=requests_per_level, concurrency=c) for c in levels]
