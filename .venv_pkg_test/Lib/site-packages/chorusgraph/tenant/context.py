"""Server-side tenant context enforcement (E6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


class TenantIsolationError(PermissionError):
    """Raised when a request crosses tenant boundaries."""


@dataclass(frozen=True)
class TenantContext:
    """Authoritative tenant scope for a request — never trust client-supplied tenant alone."""

    tenant_id: str
    subject_id: Optional[str] = None

    def assert_match(self, resource_tenant_id: str, *, layer: str = "resource") -> None:
        if resource_tenant_id != self.tenant_id:
            raise TenantIsolationError(
                f"Cross-tenant access denied at {layer}: requester={self.tenant_id} resource={resource_tenant_id}"
            )

    def scoped_key(self, key: str) -> str:
        return f"{self.tenant_id}:{key}"
