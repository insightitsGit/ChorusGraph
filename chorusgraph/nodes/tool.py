"""First-class tool node — typed signature, timeout, retry, side-effect isolation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import httpx

from chorusgraph.resilience import CallPolicy, ChorusExternalError, RetryPolicy, classify_exception, resilient_call

ToolFn = Callable[..., Any]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]
    fn: ToolFn
    timeout_seconds: float = 10.0
    max_retries: int = 2


@dataclass
class ToolResult:
    tool: str
    ok: bool
    data: Any = None
    error: Optional[str] = None
    attempts: int = 1
    duration_ms: int = 0

    def to_state_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "ok": self.ok,
            "data": self.data,
            "error": self.error,
            "attempts": self.attempts,
            "duration_ms": self.duration_ms,
        }


class ToolRegistry:
    """Registry of callable tools with isolated execution."""

    def __init__(self, *, allowlist: "ToolAllowlist | None" = None) -> None:
        from chorusgraph.security.tools import ToolAllowlist

        self._tools: Dict[str, ToolSpec] = {}
        self._allowlist = allowlist or ToolAllowlist.finance_defaults()

    def register(self, spec: ToolSpec) -> None:
        self._allowlist.validate_tool(spec.name)
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def names(self) -> List[str]:
        return sorted(self._tools.keys())

    def run(self, name: str, /, **kwargs: Any) -> ToolResult:
        from chorusgraph.security.tools import sanitize_tool_kwargs

        self._allowlist.validate_args(name, kwargs)
        safe_kwargs = sanitize_tool_kwargs(kwargs)
        return run_tool(self.get(name), **safe_kwargs)


def run_tool(spec: ToolSpec, /, **kwargs: Any) -> ToolResult:
    """Execute a tool with timeout, retry, and circuit breaker. No global state mutation."""
    started = time.perf_counter()
    policy = CallPolicy(
        timeout_seconds=spec.timeout_seconds,
        retry=RetryPolicy(max_retries=spec.max_retries),
    )
    try:
        data = resilient_call(f"tool:{spec.name}", lambda: spec.fn(**kwargs), policy=policy)
        duration_ms = int((time.perf_counter() - started) * 1000)
        return ToolResult(
            tool=spec.name,
            ok=True,
            data=data,
            attempts=1,
            duration_ms=duration_ms,
        )
    except ChorusExternalError as exc:
        detail = exc.detail
        duration_ms = int((time.perf_counter() - started) * 1000)
        return ToolResult(
            tool=spec.name,
            ok=False,
            error=detail.message,
            attempts=detail.attempts,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        detail = classify_exception(exc, service=f"tool:{spec.name}")
        duration_ms = int((time.perf_counter() - started) * 1000)
        return ToolResult(
            tool=spec.name,
            ok=False,
            error=detail.message,
            attempts=spec.max_retries + 1,
            duration_ms=duration_ms,
        )


def fetch_exchange_rate(from_currency: str, to_currency: str) -> Dict[str, Any]:
    """
    Live FX rate from Frankfurter (ECB reference data).

    https://www.frankfurter.app/ — free, no API key, real market data.
    """
    base = from_currency.strip().upper()
    quote = to_currency.strip().upper()
    if len(base) != 3 or len(quote) != 3:
        raise ValueError("Currency codes must be ISO 4217 (3 letters)")
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        resp = resilient_call(
            "frankfurter",
            lambda: client.get(
                "https://api.frankfurter.app/latest",
                params={"from": base, "to": quote},
            ),
            policy=CallPolicy.tool(),
        )
        resp.raise_for_status()
        payload = resp.json()
    rate = payload.get("rates", {}).get(quote)
    if rate is None:
        raise ValueError(f"No rate returned for {base}/{quote}")
    return {
        "from_currency": base,
        "to_currency": quote,
        "rate": float(rate),
        "date": payload.get("date"),
        "source": "frankfurter.app (ECB)",
    }


def compound_interest(
    principal: float,
    annual_rate_pct: float,
    years: float,
    compounds_per_year: int = 1,
) -> Dict[str, Any]:
    """Deterministic financial calculation — no external API."""
    if principal <= 0 or years < 0 or compounds_per_year < 1:
        raise ValueError("Invalid compound_interest parameters")
    r = annual_rate_pct / 100.0
    n = compounds_per_year
    amount = principal * (1 + r / n) ** (n * years)
    return {
        "principal": principal,
        "annual_rate_pct": annual_rate_pct,
        "years": years,
        "compounds_per_year": compounds_per_year,
        "future_value": round(amount, 2),
        "interest_earned": round(amount - principal, 2),
    }


def default_finance_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="fetch_exchange_rate",
            description="Fetch live foreign-exchange rate between two ISO currencies.",
            parameters={
                "type": "object",
                "properties": {
                    "from_currency": {"type": "string", "description": "Base currency, e.g. USD"},
                    "to_currency": {"type": "string", "description": "Quote currency, e.g. EUR"},
                },
                "required": ["from_currency", "to_currency"],
            },
            fn=fetch_exchange_rate,
            timeout_seconds=12.0,
            max_retries=2,
        )
    )
    registry.register(
        ToolSpec(
            name="compound_interest",
            description="Calculate compound interest future value.",
            parameters={
                "type": "object",
                "properties": {
                    "principal": {"type": "number"},
                    "annual_rate_pct": {"type": "number"},
                    "years": {"type": "number"},
                    "compounds_per_year": {"type": "integer", "default": 1},
                },
                "required": ["principal", "annual_rate_pct", "years"],
            },
            fn=compound_interest,
            timeout_seconds=1.0,
            max_retries=0,
        )
    )
    return registry
