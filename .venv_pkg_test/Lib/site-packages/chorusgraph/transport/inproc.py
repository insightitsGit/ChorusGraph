"""In-process transport — PrismLang envelope handoffs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from chorusgraph.transport.envelope import publish_hop, resolve_previous_artifact
from chorusgraph.transport.modes import TransportMode


@dataclass
class InProcSpine:
    """
    Same-container node communication via PrismLang envelopes (DESIGN v0.3 §3.1).

    Nodes may call ``publish`` after writing an artifact; downstream calls ``resolve``.
    """

    cache: Any
    artifact_store: Dict[str, Any]

    @property
    def mode(self) -> TransportMode:
        return TransportMode.INPROC

    def publish(
        self,
        *,
        hop: str,
        artifact: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None,
        skip_embed: bool = False,
    ) -> Dict[str, Any]:
        return publish_hop(
            cache=self.cache,
            artifact_store=self.artifact_store,
            hop=hop,
            artifact=artifact,
            state=state,
            skip_embed=skip_embed,
        )

    def resolve(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return resolve_previous_artifact(self.artifact_store, state)

    def deliver(
        self,
        *,
        from_hop: str,
        to_hop: str,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Mark handoff metadata on state (scheduler hook)."""
        return {
            "last_transport": self.mode.value,
            "last_edge": f"{from_hop}->{to_hop}",
        }


__all__ = ["InProcSpine"]
