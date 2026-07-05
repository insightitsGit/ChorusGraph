"""Health and readiness probes (E4)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, Optional

from chorusgraph.observability.metrics import get_metrics

ReadinessCheck = Callable[[], bool]


class _HealthHandler(BaseHTTPRequestHandler):
    readiness_check: Optional[ReadinessCheck] = None

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            body = health_status()
        elif self.path == "/ready":
            body = readiness_status(self.readiness_check)
        elif self.path == "/metrics":
            body = get_metrics().snapshot()
        else:
            self.send_response(404)
            self.end_headers()
            return
        payload = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def health_status() -> Dict[str, Any]:
    return {"status": "ok", "service": "chorusgraph"}


def readiness_status(check: Optional[ReadinessCheck] = None) -> Dict[str, Any]:
    ready = check() if check is not None else True
    return {"status": "ready" if ready else "not_ready", "ready": ready}


def start_health_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    *,
    readiness_check: Optional[ReadinessCheck] = None,
) -> HTTPServer:
    handler = type("BoundHealthHandler", (_HealthHandler,), {})
    handler.readiness_check = readiness_check
    server = HTTPServer((host, port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="chorusgraph-health")
    thread.start()
    return server
