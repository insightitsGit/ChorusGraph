"""CHORUS Fabric transport — cross-container spine (DESIGN v0.3 §3.2)."""

from __future__ import annotations

import asyncio
import base64
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

    def to_wire_dict(self) -> Dict[str, Any]:
        return {
            "type": "chorus_batch",
            "wire_b64": base64.b64encode(self.to_bytes()).decode("ascii"),
            "artifact_refs": list(self.artifact_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_wire_dict(cls, payload: Dict[str, Any]) -> "ChorusBatchFrame":
        wire = base64.b64decode(str(payload.get("wire_b64") or ""))
        return cls.from_bytes(wire, artifact_refs=list(payload.get("artifact_refs") or []))


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


def _run_async(coro: Any) -> Any:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


@dataclass
class ChorusSpine:
    """
    Cross-service transport via CHORUS Fabric.

    Production wiring uses ``prism.cluster.transport.ClusterTransport`` (HTTP DIRECT)
    or CHORUS/chorus_fabric gRPC client when available.
    """

    tenant_id: str
    client: Any = None
    _sent: List[ChorusFrame] = field(default_factory=list)
    _batch_sent: List[ChorusBatchFrame] = field(default_factory=list)
    _frames_received: int = 0

    @property
    def mode(self) -> TransportMode:
        if self.client is not None:
            return TransportMode.CHORUS_LOCAL
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
        if self.client is not None:
            if hasattr(self.client, "publish"):
                wire = {
                    "type": "chorus_frame",
                    "envelope_id": frame.envelope_id,
                    "vector_64": frame.vector_64,
                    "hop": frame.hop,
                    "tenant_id": frame.tenant_id,
                    "artifact_ref": frame.artifact_ref,
                    "metadata": frame.metadata,
                    "from_hop": from_hop,
                    "to_hop": to_hop,
                }
                _run_async(self.client.publish(wire))
            elif hasattr(self.client, "send_tensor"):
                self.client.send_tensor(frame)
        return {
            "last_transport": self.mode.value,
            "last_edge": f"{from_hop}->{to_hop}",
            "chorus_frame_id": frame.envelope_id,
        }

    def deliver_batch(
        self,
        batch: ChorusBatchFrame,
        *,
        from_hop: str,
        to_hop: str,
    ) -> Dict[str, Any]:
        """Send a batched (N, 64) frame — the wire unit for Send-over-transport."""
        batch.metadata.setdefault("tenant_id", self.tenant_id)
        self._batch_sent.append(batch)
        wire_bytes = len(batch.to_bytes())
        if self.client is not None and hasattr(self.client, "publish"):
            payload = batch.to_wire_dict()
            payload["from_hop"] = from_hop
            payload["to_hop"] = to_hop
            _run_async(self.client.publish(payload))
        return {
            "last_transport": self.mode.value,
            "last_edge": f"{from_hop}->{to_hop}",
            "batch_shape": batch.shape,
            "wire_bytes": wire_bytes,
            "batch_count": len(batch.vectors),
        }

    def ingest_wire(self, payload: Dict[str, Any]) -> Optional[ChorusBatchFrame]:
        """Decode an incoming cluster frame (loopback / ingest handler)."""
        self._frames_received += 1
        if payload.get("type") == "chorus_batch":
            return ChorusBatchFrame.from_wire_dict(payload)
        if payload.get("type") == "chorus_frame":
            self._sent.append(
                ChorusFrame(
                    envelope_id=str(payload.get("envelope_id") or ""),
                    vector_64=list(payload.get("vector_64") or []),
                    hop=str(payload.get("hop") or ""),
                    tenant_id=str(payload.get("tenant_id") or self.tenant_id),
                    artifact_ref=str(payload.get("artifact_ref") or ""),
                    metadata=dict(payload.get("metadata") or {}),
                )
            )
        return None


__all__ = ["ChorusBatchFrame", "ChorusFrame", "ChorusSpine", "decode_batch_frame", "encode_batch_frame"]
