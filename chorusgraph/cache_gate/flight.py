"""L1 single-flight coalescing — opt-in in-flight miss join (ADR-006)."""

from __future__ import annotations

import copy
import hashlib
import threading
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Generic, Literal, Optional, TypeVar

from chorusgraph.cache_gate.scope import normalize_exact_query
from chorusgraph.sections.models import CacheKeying, CacheProfile, CacheScope

T = TypeVar("T")

OnLeaderError = Literal["propagate", "fallthrough"]

# Keying / scope allowed to coalesce (ADR-006).
_FLIGHT_KEYINGS = frozenset({"exact", "fingerprint"})
_FLIGHT_SCOPES = frozenset({"global", "tenant"})


@dataclass(frozen=True)
class FlightPolicy:
    """Opt-in stampede control. Default ``enabled=False`` preserves today."""

    enabled: bool = False
    join_timeout_s: float = 30.0
    on_leader_error: OnLeaderError = "fallthrough"


@dataclass(frozen=True)
class FlightEligibility:
    eligible: bool
    flight_key: Optional[str] = None
    reason: str = ""


def flight_eligible(
    profile: CacheProfile,
    *,
    tenant_id: str,
    scope_id: str,
    category_slug: str,
    query: str,
    fingerprint_key: Optional[str] = None,
    policy: Optional[FlightPolicy] = None,
    profile_single_flight: Optional[bool] = None,
) -> FlightEligibility:
    """
    Return whether this miss may join a single-flight group.

    Requires policy/profile opt-in AND exact|fingerprint keying AND global|tenant scope.
    """
    pol = policy or FlightPolicy()
    want = bool(pol.enabled) or bool(
        profile_single_flight if profile_single_flight is not None else getattr(profile, "single_flight", False)
    )
    if not want:
        return FlightEligibility(False, reason="disabled")

    keying: CacheKeying = profile.keying
    scope: CacheScope = profile.scope
    if keying not in _FLIGHT_KEYINGS:
        return FlightEligibility(False, reason=f"keying={keying}")
    if scope not in _FLIGHT_SCOPES:
        return FlightEligibility(False, reason=f"scope={scope}")

    if keying == "fingerprint":
        direct = (fingerprint_key or "").strip()
        if not direct:
            return FlightEligibility(False, reason="empty_fingerprint")
    else:
        direct = normalize_exact_query(query)
        if not direct:
            return FlightEligibility(False, reason="empty_query")

    raw = "|".join(
        [
            tenant_id or "default",
            scope_id,
            category_slug,
            keying,
            direct,
        ]
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return FlightEligibility(True, flight_key=digest, reason="ok")


class _Flight(Generic[T]):
    __slots__ = ("_event", "_result", "_error", "_cancelled", "_lock")

    def __init__(self) -> None:
        self._event = threading.Event()
        self._result: Optional[T] = None
        self._error: Optional[BaseException] = None
        self._cancelled = False
        self._lock = threading.Lock()

    def set_result(self, value: T) -> None:
        with self._lock:
            self._result = value
            self._error = None
            self._cancelled = False
        self._event.set()

    def set_error(self, exc: BaseException) -> None:
        with self._lock:
            self._error = exc
            self._result = None
            self._cancelled = False
        self._event.set()

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            self._result = None
            self._error = None
        self._event.set()

    def wait(self, timeout_s: float) -> bool:
        return self._event.wait(timeout=timeout_s)

    def snapshot(self) -> tuple[bool, Optional[T], Optional[BaseException], bool]:
        with self._lock:
            return self._event.is_set(), self._result, self._error, self._cancelled


class InProcessFlightCoordinator:
    """
    Process-local single-flight map.

    One leader computes; followers wait for the same key or time out and compute.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._flights: Dict[str, _Flight[Any]] = {}

    def run(
        self,
        key: str,
        compute: Callable[[], T],
        *,
        timeout_s: float = 30.0,
        on_leader_error: OnLeaderError = "fallthrough",
    ) -> T:
        flight, is_leader = self._begin(key)
        if is_leader:
            return self._lead(key, flight, compute)
        return self._follow_sync(key, flight, compute, timeout_s=timeout_s, on_leader_error=on_leader_error)

    async def arun(
        self,
        key: str,
        compute: Callable[[], Awaitable[T]],
        *,
        timeout_s: float = 30.0,
        on_leader_error: OnLeaderError = "fallthrough",
    ) -> T:
        import asyncio

        flight, is_leader = self._begin(key)
        if is_leader:
            return await self._alead(key, flight, compute)
        return await self._afollow(
            key, flight, compute, timeout_s=timeout_s, on_leader_error=on_leader_error
        )

    def _begin(self, key: str) -> tuple[_Flight[Any], bool]:
        with self._lock:
            existing = self._flights.get(key)
            if existing is None:
                flight: _Flight[Any] = _Flight()
                self._flights[key] = flight
                return flight, True
            return existing, False

    def _release(self, key: str, flight: _Flight[Any]) -> None:
        with self._lock:
            if self._flights.get(key) is flight:
                del self._flights[key]

    def _lead(self, key: str, flight: _Flight[Any], compute: Callable[[], T]) -> T:
        try:
            result = compute()
            flight.set_result(result)
            return result
        except BaseException as exc:
            # Control-flow interrupts: cancel waiters so they fall through.
            if _is_control_flow(exc):
                flight.cancel()
                raise
            flight.set_error(exc)
            raise
        finally:
            self._release(key, flight)

    async def _alead(self, key: str, flight: _Flight[Any], compute: Callable[[], Awaitable[T]]) -> T:
        try:
            result = await compute()
            flight.set_result(result)
            return result
        except BaseException as exc:
            if _is_control_flow(exc):
                flight.cancel()
                raise
            flight.set_error(exc)
            raise
        finally:
            self._release(key, flight)

    def _follow_sync(
        self,
        key: str,
        flight: _Flight[Any],
        compute: Callable[[], T],
        *,
        timeout_s: float,
        on_leader_error: OnLeaderError,
    ) -> T:
        ok = flight.wait(timeout_s)
        return self._resolve_follower(ok, flight, compute, on_leader_error=on_leader_error)

    async def _afollow(
        self,
        key: str,
        flight: _Flight[Any],
        compute: Callable[[], Awaitable[T]],
        *,
        timeout_s: float,
        on_leader_error: OnLeaderError,
    ) -> T:
        import asyncio

        ok = await asyncio.to_thread(flight.wait, timeout_s)
        done, result, error, cancelled = flight.snapshot()
        if not ok or cancelled or not done:
            return await compute()
        if error is not None:
            if on_leader_error == "propagate":
                raise error
            return await compute()
        return copy.deepcopy(result)  # type: ignore[return-value]

    def _resolve_follower(
        self,
        waited_ok: bool,
        flight: _Flight[Any],
        compute: Callable[[], T],
        *,
        on_leader_error: OnLeaderError,
    ) -> T:
        done, result, error, cancelled = flight.snapshot()
        if not waited_ok or cancelled or not done:
            return compute()
        if error is not None:
            if on_leader_error == "propagate":
                raise error
            return compute()
        return copy.deepcopy(result)  # type: ignore[return-value]


def _is_control_flow(exc: BaseException) -> bool:
    from chorusgraph.core.node import NodeInterrupt
    from chorusgraph.core.pending_writes import MidStepAbort
    from chorusgraph.core.scheduler import GraphInterrupt

    return isinstance(exc, (NodeInterrupt, GraphInterrupt, MidStepAbort))


def resolve_flight_policy(
    *,
    runtime_policy: Optional[FlightPolicy],
    spec_policy: Optional[FlightPolicy],
    profile: CacheProfile,
) -> FlightPolicy:
    """Node spec overrides runtime; profile.single_flight can enable when policy disabled."""
    base = spec_policy or runtime_policy or FlightPolicy()
    if base.enabled:
        return base
    if getattr(profile, "single_flight", False):
        timeout = getattr(profile, "single_flight_timeout_s", None)
        return FlightPolicy(
            enabled=True,
            join_timeout_s=float(timeout) if timeout is not None else base.join_timeout_s,
            on_leader_error=base.on_leader_error,
        )
    return base


__all__ = [
    "FlightEligibility",
    "FlightPolicy",
    "InProcessFlightCoordinator",
    "flight_eligible",
    "resolve_flight_policy",
]
