"""Partial run result contract (E2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from chorusgraph.resilience.errors import ExternalError


@dataclass
class PartialRunResult:
    """Caller-facing partial outcome when one node or dependency fails."""

    ok: bool
    values: Dict[str, Any] = field(default_factory=dict)
    errors: List[ExternalError] = field(default_factory=list)
    run_id: Optional[str] = None

    def to_state_dict(self) -> Dict[str, Any]:
        out = dict(self.values)
        if self.errors:
            out["__partial__"] = True
            out["__errors__"] = [
                {
                    "service": e.service,
                    "code": e.code,
                    "message": e.message,
                    "kind": e.kind.value,
                    "retryable": e.retryable,
                }
                for e in self.errors
            ]
        return out
