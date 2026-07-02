"""Transport spine factory — selects PrismLang / CHORUS / PrismAPI per edge."""

from __future__ import annotations

from typing import Any, Dict, Optional

from chorusgraph.engine.context import PrismEngineContext
from chorusgraph.transport.chorus import ChorusSpine
from chorusgraph.transport.inproc import InProcSpine
from chorusgraph.transport.modes import DEFAULT_TRANSPORT, TransportMode
from chorusgraph.transport.prismapi import PrismAPISpine


class TransportSpine:
    """Facade routing edge delivery to the correct Prism transport product."""

    def __init__(self, context: PrismEngineContext) -> None:
        self._ctx = context
        self._inproc = InProcSpine(
            cache=context.cache,
            artifact_store=context.artifact_store(),
        )
        self._chorus = ChorusSpine(tenant_id=context.tenant_id, client=context.chorus_client)
        self._prismapi = PrismAPISpine(tenant_id=context.tenant_id, client=context.prismapi_client)

    def for_mode(self, mode: TransportMode) -> Any:
        if mode == TransportMode.INPROC:
            return self._inproc
        if mode == TransportMode.CHORUS_LOCAL:
            return self._chorus
        if mode == TransportMode.CHORUS_FEDERATED:
            return self._prismapi
        raise ValueError(f"Unknown transport mode: {mode}")

    def edge_handoff(
        self,
        *,
        mode: TransportMode,
        from_hop: str,
        to_hop: str,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Scheduler hook after ``from_hop`` completes, before ``to_hop`` runs."""
        spine = self.for_mode(mode or DEFAULT_TRANSPORT)
        if mode == TransportMode.INPROC:
            return spine.deliver(from_hop=from_hop, to_hop=to_hop, state=state)
        if mode == TransportMode.CHORUS_LOCAL:
            env_id = state.get("latest_envelope_id") or ""
            vec = state.get("query_vector_64") or []
            frame = spine.encode_frame(
                envelope_id=str(env_id),
                vector_64=list(vec) if vec else [],
                hop=from_hop,
                artifact_ref=str(env_id),
            )
            return spine.deliver(frame, from_hop=from_hop, to_hop=to_hop)
        return {"last_transport": mode.value, "last_edge": f"{from_hop}->{to_hop}"}


def build_spine(context: Optional[PrismEngineContext] = None) -> Optional[TransportSpine]:
    if context is None:
        return None
    return TransportSpine(context)


__all__ = ["TransportSpine", "build_spine"]
