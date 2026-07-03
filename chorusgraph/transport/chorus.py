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
class ChorusBatchFrame:
    """N branch envelopes batched as (N, 64) float32 vectors + artifact refs (T6)."""

    vectors: List[List[float]]
    artifact_refs: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def shape(self) -> tuple[int, int]:
        n = len(self.vectors)
        dim = len(self.vectors[0]) if self.vectors else 64
        return (n, dim)

    def to_bytes(self) -> bytes:
        import struct

        buf = bytearray()
        buf.extend(struct.pack("<II", len(self.vectors), len(self.vectors[0]) if self.vectors else 64))
        for row in self.vectors:
            buf.extend(struct.pack(f"<{len(row)}f", *[float(x) for x in row]))
        return bytes(buf)

    @classmethod
    def from_bytes(cls, data: bytes, *, artifact_refs: List[str]) -> "ChorusBatchFrame":
        import struct

        n, dim = struct.unpack("<II", data[:8])
        offset = 8
        vectors: List[List[float]] = []
        for _ in range(n):
            row = list(struct.unpack(f"<{dim}f", data[offset : offset + dim * 4]))
            vectors.append(row)
            offset += dim * 4
        return cls(vectors=vectors, artifact_refs=list(artifact_refs))


def encode_batch_frame(frames: List[ChorusFrame]) -> ChorusBatchFrame:
    return ChorusBatchFrame(
        vectors=[list(f.vector_64) for f in frames],
        artifact_refs=[f.artifact_ref for f in frames],
        metadata={"count": len(frames)},
    )


def decode_batch_frame(batch: ChorusBatchFrame) -> List[ChorusFrame]:
    out: List[ChorusFrame] = []
    for idx, vector in enumerate(batch.vectors):
        out.append(
            ChorusFrame(
                envelope_id=f"batch-{idx}",
                vector_64=list(vector),
                hop="batch",
                tenant_id=str(batch.metadata.get("tenant_id") or "default"),
                artifact_ref=batch.artifact_refs[idx] if idx < len(batch.artifact_refs) else "",
            )
        )
    return out


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


__all__ = ["ChorusBatchFrame", "ChorusFrame", "ChorusSpine", "decode_batch_frame", "encode_batch_frame"]
