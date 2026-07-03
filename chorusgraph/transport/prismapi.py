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

    Wired to ``prism.api.consumer.PrismAPIClient`` (loopback or HTTP) when
    ``client`` is provided.  Boundary re-projection uses ``boundary_translator``
    (typically ``PrismProjector`` at the tenant edge).
    """

    tenant_id: str
    client: Any = None
    boundary_translator: Any = None
    _calls: List[RemoteQuery] = field(default_factory=list)
    remote_embed_calls: int = 0

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

        if self.client is not None and hasattr(self.client, "query"):
            raw = self.client.query(query_text, top_k=int(metadata.get("top_k", 10) if metadata else 10))
            chunks = []
            for sem, side in getattr(raw, "results", []) or []:
                chunks.append(
                    {
                        "doc_id": getattr(sem, "doc_id", ""),
                        "vector": list(getattr(sem, "vector", []) or []),
                        "fields": dict(getattr(side, "fields", {}) or {}),
                    }
                )
            return RemoteResponse(
                provider_id=provider_id,
                kb_context=chunks,
                category_slug=category_slug,
                metadata={"request_id": getattr(raw, "request_id", "")},
            )

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

    def route_envelope(self, encoded: Dict[str, Any]) -> Dict[str, Any]:
        """Route a boundary envelope through PrismAPI (vector-only on remote side)."""
        self._calls.append(
            RemoteQuery(
                provider_id="subgraph",
                query_text=str(encoded.get("artifact_ref") or ""),
                category_slug="subgraph",
                tenant_id=self.tenant_id,
                metadata={"encoded": encoded},
            )
        )
        vector = list(encoded.get("vector_64") or [0.0] * 64)
        if self.boundary_translator is not None and hasattr(self.boundary_translator, "project"):
            import numpy as np

            try:
                env = self.boundary_translator.project(np.asarray(vector, dtype=np.float32))
                vector = [float(x) for x in env.vector]
            except Exception:
                pass

        if self.client is not None and hasattr(self.client, "query_vector"):
            import numpy as np

            self.client.query_vector(np.asarray(vector, dtype=np.float32), top_k=1)
            embedder = getattr(self.client, "_embedder", None)
            if embedder is not None and hasattr(embedder, "call_count"):
                self.remote_embed_calls = int(getattr(embedder, "call_count", 0))

        return {
            "envelope_id": encoded.get("envelope_id"),
            "vector_64": vector,
            "artifact_ref": encoded.get("artifact_ref"),
            "metadata": {"routed_via": self.mode.value, "stub": self.client is None},
        }

    def route_batch(self, batch: Any) -> Dict[str, Any]:
        """Accept a ChorusBatchFrame metadata record for federation accounting."""
        self._calls.append(
            RemoteQuery(
                provider_id="send_batch",
                query_text=f"batch:{getattr(batch, 'shape', ())}",
                category_slug="subgraph",
                tenant_id=self.tenant_id,
                metadata={"batch": True},
            )
        )
        return {"routed_via": self.mode.value, "batch_shape": getattr(batch, "shape", ())}


__all__ = ["PrismAPISpine", "RemoteQuery", "RemoteResponse"]
