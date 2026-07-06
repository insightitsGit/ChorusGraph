"""Federation authn/authz for PrismAPI (E3 §21)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Optional, Set


class AuthorizationError(PermissionError):
    """Raised when a federated call lacks auth or tenant scope."""


@dataclass
class FederationAuthContext:
    """Mutual-auth context attached to federated PrismAPI calls."""

    caller_tenant_id: str
    bearer_token: Optional[str] = None
    allowed_providers: FrozenSet[str] = field(default_factory=frozenset)
    roles: FrozenSet[str] = field(default_factory=frozenset)

    def authorize(
        self,
        *,
        target_tenant_id: str,
        provider_id: str,
        action: str = "federated_retrieve",
    ) -> None:
        if not self.bearer_token:
            raise AuthorizationError("Missing bearer token for federated call")
        if self.caller_tenant_id != target_tenant_id:
            raise AuthorizationError(
                f"Cross-tenant federated access denied: {self.caller_tenant_id} -> {target_tenant_id}"
            )
        if self.allowed_providers and provider_id not in self.allowed_providers:
            raise AuthorizationError(f"Provider not authorized: {provider_id}")
        if action not in self._permitted_actions():
            raise AuthorizationError(f"Action not permitted: {action}")

    @staticmethod
    def _permitted_actions() -> Set[str]:
        return {"federated_retrieve", "query", "query_vector", "subgraph"}
