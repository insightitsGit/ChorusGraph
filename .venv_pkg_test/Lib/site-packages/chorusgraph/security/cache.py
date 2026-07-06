"""Cache write-authorization and per-tenant isolation (E3 §21)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set


class CacheSecurityError(PermissionError):
    """Raised on cache poisoning or cross-tenant write attempts."""


@dataclass
class CacheSecurityGuard:
    """Enforces tenant-scoped cache keys and write authorization."""

    tenant_id: str
    trusted_writers: Set[str] = field(default_factory=lambda: {"cache_gate", "seed_policy", "system"})
    require_provenance: bool = True

    def authorize_write(
        self,
        *,
        writer: str,
        entry_tenant_id: str,
        provenance: Optional[Dict[str, Any]] = None,
        user_generated: bool = False,
    ) -> None:
        if entry_tenant_id != self.tenant_id:
            raise CacheSecurityError(
                f"Cross-tenant cache write blocked: writer tenant={entry_tenant_id} guard={self.tenant_id}"
            )
        if writer not in self.trusted_writers:
            raise CacheSecurityError(f"Untrusted cache writer: {writer}")
        if user_generated:
            raise CacheSecurityError("User-generated cache sections cannot be written to shared cache")
        if self.require_provenance and not provenance:
            raise CacheSecurityError("Cache write missing provenance metadata")

    def scoped_key(self, base_key: str) -> str:
        return f"{self.tenant_id}:{base_key}"

    def assert_read_scope(self, entry_tenant_id: str) -> None:
        if entry_tenant_id != self.tenant_id:
            raise CacheSecurityError(
                f"Cross-tenant cache read blocked: entry={entry_tenant_id} requester={self.tenant_id}"
            )
