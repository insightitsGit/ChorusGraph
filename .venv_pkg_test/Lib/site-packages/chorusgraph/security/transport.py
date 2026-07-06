"""Transport security — TLS default, CHORUS cipher opt-in only (E3 §21)."""

from __future__ import annotations

import os
from dataclasses import dataclass


class TransportSecurityError(PermissionError):
    """Raised when transport config violates security policy."""


@dataclass(frozen=True)
class TransportSecurityPolicy:
    """
    Default: standard TLS/mTLS required; homegrown CHORUS cipher OFF until audited.

    Set ``CHORUSGRAPH_CHORUS_CIPHER=1`` to opt in explicitly (not a security guarantee).
    """

    tls_required: bool = True
    mtls_required: bool = False
    chorus_cipher_enabled: bool = False

    @classmethod
    def from_env(cls) -> "TransportSecurityPolicy":
        chorus = os.environ.get("CHORUSGRAPH_CHORUS_CIPHER", "").strip().lower() in ("1", "true", "yes")
        tls_off = os.environ.get("CHORUSGRAPH_TLS_OFF", "").strip().lower() in ("1", "true", "yes")
        mtls = os.environ.get("CHORUSGRAPH_MTLS", "").strip().lower() in ("1", "true", "yes")
        return cls(tls_required=not tls_off, mtls_required=mtls, chorus_cipher_enabled=chorus)

    def validate_endpoint(self, url: str) -> None:
        if not self.tls_required:
            return
        if url.startswith("http://") and not url.startswith("http://127.0.0.1") and not url.startswith("http://localhost"):
            raise TransportSecurityError(
                "Plain HTTP blocked by transport policy — use HTTPS or set CHORUSGRAPH_TLS_OFF=1 for dev only"
            )

    def effective_cipher_mode(self) -> str:
        if self.chorus_cipher_enabled:
            return "chorus_opt_in"
        return "tls"
