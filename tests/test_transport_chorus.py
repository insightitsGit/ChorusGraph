"""T6 — CHORUS mesh transport wire tests."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from chorusgraph.core.transport_router import TransportRouter
from chorusgraph.transport.chorus import (
    ChorusBatchFrame,
    ChorusFrame,
    ChorusSpine,
    encode_batch_frame,
)
from chorusgraph.transport.modes import TransportMode


class _IngestHandler(BaseHTTPRequestHandler):
    received: list[dict[str, Any]] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        payload = json.loads(body.decode("utf-8"))
        _IngestHandler.received.append(payload)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def _start_server() -> tuple[HTTPServer, threading.Thread]:
    _IngestHandler.received = []
    server = HTTPServer(("127.0.0.1", 0), _IngestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_chorus_batch_frame_wire_roundtrip():
    frames = [
        ChorusFrame(
            envelope_id=f"e{i}",
            vector_64=[float(i)] * 64,
            hop="h",
            tenant_id="t",
            artifact_ref=f"ref-{i}",
        )
        for i in range(3)
    ]
    batch = encode_batch_frame(frames)
    wire = batch.to_bytes()
    restored = ChorusBatchFrame.from_bytes(wire, artifact_refs=batch.artifact_refs)
    assert restored.shape == (3, 64)
    assert restored.vectors[1][0] == 1.0


def test_cluster_transport_loopback_http():
    httpx = pytest.importorskip("httpx")
    from prism.cluster.transport import ClusterTransport
    from prism.cluster.transport import TransportMode as ClusterMode

    server, thread = _start_server()
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"

    transport = ClusterTransport("node-a", peers={"peer": base_url}, mode=ClusterMode.DIRECT)
    batch = ChorusBatchFrame(
        vectors=[[1.0] * 64, [2.0] * 64],
        artifact_refs=["a", "b"],
        metadata={"tenant_id": "wire-test"},
    )
    spine = ChorusSpine(tenant_id="wire-test", client=transport)
    out = spine.deliver_batch(batch, from_hop="map", to_hop="worker")
    assert out["batch_count"] == 2
    time.sleep(0.2)

    server.shutdown()
    thread.join(timeout=2)

    assert _IngestHandler.received
    payload = _IngestHandler.received[0]
    assert payload.get("type") == "chorus_batch"
    decoded = ChorusBatchFrame.from_wire_dict(payload)
    assert decoded.shape == (2, 64)
    assert decoded.vectors[0][0] == 1.0


def test_transport_router_batch_delivery():
    router = TransportRouter(
        tenant_id="t",
        mode=TransportMode.CHORUS_LOCAL,
        chorus=ChorusSpine(tenant_id="t"),
    )
    batch = ChorusBatchFrame(vectors=[[0.0] * 64], artifact_refs=["x"])
    router.deliver_batch(batch, from_hop="a", to_hop="b")
    assert router.batch_deliveries == 1
    assert router.wire_bytes > 0
