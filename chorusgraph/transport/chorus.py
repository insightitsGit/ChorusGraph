"""CHORUS Fabric transport — cross-container spine (DESIGN v0.3 §3.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from chorusgraph.transport.modes import TransportMode


@dataclass
class ChorusFrame:
    """Serialized Prism envelope + artifact reference for CHORUS gRPC."""

    envelope_id: str
    vector_64: List[float]
    hop: str
    tenant_id: str
    artifact_ref: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChorusSpine:
    """
    Cross-service transport via CHORUS Fabric.

    Production wiring uses ``CHORUS/chorus_fabric/`` gRPC client.
    This class defines the engine contract and supports in-memory simulation for tests.
    """

    tenant_id: str
    client: Any = None
    _sent: List[ChorusFrame] = field(default_factory=list)

    @property
    def mode(self) -> TransportMode:
        return TransportMode.CHORUS_LOCAL

    def encode_frame(
        self,
        *,
        envelope_id: str,
        vector_64: List[float],
        hop: str,
        artifact_ref: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChorusFrame:
        return ChorusFrame(
            envelope_id=envelope_id,
            vector_64=list(vector_64),
            hop=hop,
            tenant_id=self.tenant_id,
            artifact_ref=artifact_ref,
            metadata=dict(metadata or {}),
        )

    def deliver(
        self,
        frame: ChorusFrame,
        *,
        from_hop: str,
        to_hop: str,
    ) -> Dict[str, Any]:
        """Send frame over CHORUS (or record for tests when client is None)."""
        self._sent.append(frame)
        if self.client is not None and hasattr(self.client, "send_tensor"):
            self.client.send_tensor(frame)
        return {
            "last_transport": self.mode.value,
            "last_edge": f"{from_hop}->{to_hop}",
            "chorus_frame_id": frame.envelope_id,
        }


__all__ = ["ChorusFrame", "ChorusSpine"]
