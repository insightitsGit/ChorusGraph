"""PrismAPI federated transport — cross-tenant remote nodes (DESIGN v0.3 §3.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from chorusgraph.transport.modes import TransportMode


@dataclass
class RemoteQuery:
    provider_id: str
    query_text: str
    category_slug: str
    tenant_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RemoteResponse:
    provider_id: str
    kb_context: List[Dict[str, Any]]
    category_slug: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PrismAPISpine:
    """
    Federated retrieval / remote subgraph over CHORUS (PrismAPI).

    Maps to built-in ``remote`` node kind in DESIGN §7.1.
    """

    tenant_id: str
    client: Any = None
    _calls: List[RemoteQuery] = field(default_factory=list)

    @property
    def mode(self) -> TransportMode:
        return TransportMode.CHORUS_FEDERATED

    def invoke(
        self,
        *,
        provider_id: str,
        query_text: str,
        category_slug: str = "knowledge",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RemoteResponse:
        query = RemoteQuery(
            provider_id=provider_id,
            query_text=query_text,
            category_slug=category_slug,
            tenant_id=self.tenant_id,
            metadata=dict(metadata or {}),
        )
        self._calls.append(query)

        if self.client is not None and hasattr(self.client, "federated_retrieve"):
            raw = self.client.federated_retrieve(query)
            chunks = raw.get("chunks") or []
            return RemoteResponse(
                provider_id=provider_id,
                kb_context=list(chunks),
                category_slug=category_slug,
                metadata=dict(raw.get("metadata") or {}),
            )

        return RemoteResponse(
            provider_id=provider_id,
            kb_context=[],
            category_slug=category_slug,
            metadata={"stub": True},
        )

    def to_state_update(self, response: RemoteResponse) -> Dict[str, Any]:
        return {
            "kb_context": response.kb_context,
            "remote_provider": response.provider_id,
            "last_transport": self.mode.value,
        }


__all__ = ["PrismAPISpine", "RemoteQuery", "RemoteResponse"]
