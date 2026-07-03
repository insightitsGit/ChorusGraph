"""Transport mode selection — in-proc / Redis / CHORUS / PrismAPI (P5/P6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from chorusgraph.transport.chorus import ChorusFrame, ChorusSpine
from chorusgraph.transport.modes import TransportMode


class FederationMode(str, Enum):
    LOCAL = "local"
    CLUSTER = "cluster"
    FEDERATED = "federated"


@dataclass
class TransportRouter:
    """
    Selects communication path per ENGINE §2.4:

    - same process → Resonance InProcessBroadcast
    - same cluster → RedisBroadcast + CHORUS
    - cross-container → PrismAPI + BoundaryTranslator
    """

    tenant_id: str
    mode: TransportMode = TransportMode.INPROC
    chorus: Optional[ChorusSpine] = None
    prismapi_client: Any = None
    _deliveries: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def for_agents(cls, tenant_id: str, *, local: bool, same_cluster: bool) -> "TransportRouter":
        if local:
            return cls(tenant_id=tenant_id, mode=TransportMode.INPROC)
        if same_cluster:
            return cls(
                tenant_id=tenant_id,
                mode=TransportMode.CHORUS_LOCAL,
                chorus=ChorusSpine(tenant_id=tenant_id),
            )
        return cls(
            tenant_id=tenant_id,
            mode=TransportMode.CHORUS_FEDERATED,
            chorus=ChorusSpine(tenant_id=tenant_id),
        )

    def deliver_envelope(
        self,
        *,
        envelope_id: str,
        vector_64: List[float],
        hop: str,
        artifact_ref: str,
        from_hop: str,
        to_hop: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if self.mode == TransportMode.INPROC:
            record = {
                "transport": self.mode.value,
                "from": from_hop,
                "to": to_hop,
                "envelope_id": envelope_id,
            }
            self._deliveries.append(record)
            return record

        if self.mode in (TransportMode.CHORUS_LOCAL, TransportMode.CHORUS_FEDERATED):
            assert self.chorus is not None
            frame = self.chorus.encode_frame(
                envelope_id=envelope_id,
                vector_64=vector_64,
                hop=hop,
                artifact_ref=artifact_ref,
                metadata=metadata,
            )
            result = self.chorus.deliver(frame, from_hop=from_hop, to_hop=to_hop)
            self._deliveries.append(result)
            return result

        if self.prismapi_client is not None:
            record = {
                "transport": "prismapi",
                "from": from_hop,
                "to": to_hop,
                "envelope_id": envelope_id,
            }
            if hasattr(self.prismapi_client, "federate"):
                self.prismapi_client.federate(
                    from_agent=from_hop,
                    to_agent=to_hop,
                    vector=vector_64,
                    metadata=metadata or {},
                )
            self._deliveries.append(record)
            return record

        return {"transport": self.mode.value, "skipped": True}

    @property
    def deliveries(self) -> List[Dict[str, Any]]:
        return list(self._deliveries)


__all__ = ["FederationMode", "TransportRouter"]
