"""Edge transport modes for the Prism spine (DESIGN v0.3 §3)."""

from __future__ import annotations

from enum import Enum


class TransportMode(str, Enum):
    """How state/handoffs move between nodes."""

    INPROC = "inproc"
    """Same process — PrismLang PrismEnvelope on state (default)."""

    CHORUS_LOCAL = "chorus_local"
    """Same cluster, different service — CHORUS Fabric gRPC tensor frame."""

    CHORUS_FEDERATED = "chorus_federated"
    """Cross-tenant/network — PrismAPI over CHORUS."""


DEFAULT_TRANSPORT = TransportMode.INPROC

__all__ = ["DEFAULT_TRANSPORT", "TransportMode"]
