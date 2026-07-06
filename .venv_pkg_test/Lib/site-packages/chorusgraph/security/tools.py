"""Tool allowlist and argument validation (E3 §21)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Iterable, Mapping, Set


class ToolSecurityError(PermissionError):
    """Raised when a tool call violates sandbox policy."""


_INJECTION_PATTERNS = (
    re.compile(r"(?i)\b(rm\s+-rf|curl\s+.*\||wget\s+|eval\s*\(|exec\s*\(|__import__)\b"),
    re.compile(r"(?i)(/etc/passwd|file://|javascript:|<script)"),
)


@dataclass
class ToolAllowlist:
    """Per-registry allowlist of tool names and permitted argument keys."""

    allowed_tools: FrozenSet[str] = field(default_factory=frozenset)
    allowed_arg_keys: Mapping[str, FrozenSet[str]] = field(default_factory=dict)

    @classmethod
    def finance_defaults(cls) -> "ToolAllowlist":
        return cls(
            allowed_tools=frozenset({"fetch_exchange_rate", "compound_interest"}),
            allowed_arg_keys={
                "fetch_exchange_rate": frozenset({"from_currency", "to_currency"}),
                "compound_interest": frozenset(
                    {"principal", "annual_rate_pct", "years", "compounds_per_year"}
                ),
            },
        )

    def validate_tool(self, name: str) -> None:
        if self.allowed_tools and name not in self.allowed_tools:
            raise ToolSecurityError(f"Tool not allowlisted: {name}")

    def validate_args(self, name: str, kwargs: Dict[str, Any]) -> None:
        self.validate_tool(name)
        permitted = self.allowed_arg_keys.get(name)
        if permitted is not None:
            extra = set(kwargs) - set(permitted)
            if extra:
                raise ToolSecurityError(f"Disallowed arguments for {name}: {sorted(extra)}")
        for key, value in kwargs.items():
            if isinstance(value, str):
                scan_string(value, context=f"{name}.{key}")


def scan_string(value: str, *, context: str = "arg") -> None:
    """Reject obvious injection / SSRF patterns in tool arguments."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(value):
            raise ToolSecurityError(f"Blocked unsafe content in {context}")


def sanitize_tool_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow copy with string values scanned."""
    out: Dict[str, Any] = {}
    for key, value in kwargs.items():
        if isinstance(value, str):
            scan_string(value, context=key)
            out[key] = value.strip()
        else:
            out[key] = value
    return out
