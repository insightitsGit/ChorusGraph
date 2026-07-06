"""Native checkpoint persistence — prismlang checkpointers (P2)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Set

from chorusgraph.core.channels import ChannelState, NodeUpdate
from chorusgraph.core.pending_writes import PendingWriteStore, node_update_to_dict, pending_store_for_backend


@dataclass
class GraphStateSnapshot:
    """Point-in-time graph state for resume / time-travel."""

    values: Dict[str, Any]
    next: tuple[str, ...] = ()
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    parent_config: Optional[Dict[str, Any]] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_to_checkpoint(
    state: ChannelState,
    *,
    super_step: int,
    active: Set[str],
    graph_id: str,
    tenant_id: str,
) -> Dict[str, Any]:
    """Build a LangGraph-compatible checkpoint dict from channel state."""
    values = state.to_checkpoint_values()
    values.setdefault("tenant_id", tenant_id)
    values.setdefault("graph_id", graph_id)
    return {
        "v": 1,
        "id": str(uuid.uuid4()),
        "ts": _now_iso(),
        "channel_values": values,
        "channel_versions": {k: super_step for k in values},
        "versions_seen": {},
        "pending_sends": [],
    }


def state_from_checkpoint(checkpoint: Dict[str, Any]) -> ChannelState:
    """Restore channel state from a checkpoint dict."""
    values = checkpoint.get("channel_values") or {}
    return ChannelState.from_checkpoint_values(values)


def metadata_for_step(
    *,
    super_step: int,
    active: Set[str],
    graph_id: str,
    tenant_id: str,
    source: str = "loop",
    **extra: Any,
) -> Dict[str, Any]:
    meta = {
        "step": super_step,
        "source": source,
        "writes": {},
        "graph_id": graph_id,
        "tenant_id": tenant_id,
        "active_nodes": sorted(active),
    }
    meta.update(extra)
    return meta


@dataclass
class EngineCheckpointer:
    """
    Thin adapter over prismlang JsonFileCheckpointer / AsyncJsonFileCheckpointer.

    Stores ChannelState snapshots at each super-step boundary.
    """

    backend: Any
    _pending: Optional[PendingWriteStore] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self._pending is None:
            self._pending = pending_store_for_backend(self.backend)

    def put_writes(
        self,
        config: Dict[str, Any],
        super_step: int,
        node_id: str,
        update: NodeUpdate,
    ) -> None:
        if self._pending is not None:
            self._pending.put(config, super_step, node_id, update)
        if hasattr(self.backend, "put_writes"):
            task_id = f"{super_step}:{node_id}"
            self.backend.put_writes(config, [("node_update", node_update_to_dict(update))], task_id)

    async def aput_writes(
        self,
        config: Dict[str, Any],
        super_step: int,
        node_id: str,
        update: NodeUpdate,
    ) -> None:
        self.put_writes(config, super_step, node_id, update)
        if hasattr(self.backend, "aput_writes"):
            task_id = f"{super_step}:{node_id}"
            try:
                await self.backend.aput_writes(
                    config,
                    [("node_update", node_update_to_dict(update))],
                    task_id,
                )
            except NotImplementedError:
                pass

    def get_pending_writes(self, config: Dict[str, Any], super_step: int) -> Dict[str, NodeUpdate]:
        if self._pending is None:
            return {}
        return self._pending.list_for_step(config, super_step)

    def clear_pending_writes(self, config: Dict[str, Any], super_step: int) -> None:
        if self._pending is not None:
            self._pending.clear_step(config, super_step)

    def has_pending_writes(self, config: Dict[str, Any], super_step: int) -> bool:
        if self._pending is None:
            return False
        return self._pending.has_step(config, super_step)

    def put(
        self,
        config: Dict[str, Any],
        state: ChannelState,
        *,
        super_step: int,
        active: Set[str],
        graph_id: str,
        tenant_id: str,
        metadata_extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        checkpoint = state_to_checkpoint(
            state,
            super_step=super_step,
            active=active,
            graph_id=graph_id,
            tenant_id=tenant_id,
        )
        metadata = metadata_for_step(
            super_step=super_step,
            active=active,
            graph_id=graph_id,
            tenant_id=tenant_id,
            **(metadata_extra or {}),
        )
        return self.backend.put(config, checkpoint, metadata, {})

    def fork(
        self,
        config: Dict[str, Any],
        state: ChannelState,
        *,
        super_step: int,
        active: Set[str],
        graph_id: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Create a branched checkpoint; parent_config chains from ``config``."""
        return self.put(
            config,
            state,
            super_step=super_step,
            active=active,
            graph_id=graph_id,
            tenant_id=tenant_id,
        )

    async def aput(
        self,
        config: Dict[str, Any],
        state: ChannelState,
        *,
        super_step: int,
        active: Set[str],
        graph_id: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        checkpoint = state_to_checkpoint(
            state,
            super_step=super_step,
            active=active,
            graph_id=graph_id,
            tenant_id=tenant_id,
        )
        metadata = metadata_for_step(
            super_step=super_step,
            active=active,
            graph_id=graph_id,
            tenant_id=tenant_id,
        )
        return await self.backend.aput(config, checkpoint, metadata, {})

    def get_tuple(self, config: Dict[str, Any]) -> Optional[Any]:
        return self.backend.get_tuple(config)

    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[Any]:
        if hasattr(self.backend, "aget_tuple"):
            return await self.backend.aget_tuple(config)
        return self.backend.get_tuple(config)

    def list_history(
        self,
        config: Dict[str, Any],
        *,
        limit: Optional[int] = None,
    ) -> List[GraphStateSnapshot]:
        out: List[GraphStateSnapshot] = []
        for tup in self.backend.list(config, limit=limit):
            meta = tup.metadata or {}
            active = meta.get("active_nodes") or []
            out.append(
                GraphStateSnapshot(
                    values=dict(tup.checkpoint.get("channel_values") or {}),
                    next=tuple(active),
                    config=dict(tup.config or {}),
                    metadata=dict(meta),
                    created_at=tup.checkpoint.get("ts"),
                    parent_config=tup.parent_config,
                )
            )
        return out

    async def alist_history(
        self,
        config: Dict[str, Any],
        *,
        limit: Optional[int] = None,
    ) -> List[GraphStateSnapshot]:
        if hasattr(self.backend, "alist"):
            out: List[GraphStateSnapshot] = []
            async for tup in self.backend.alist(config, limit=limit):
                meta = tup.metadata or {}
                active = meta.get("active_nodes") or []
                out.append(
                    GraphStateSnapshot(
                        values=dict(tup.checkpoint.get("channel_values") or {}),
                        next=tuple(active),
                        config=dict(tup.config or {}),
                        metadata=dict(meta),
                        created_at=tup.checkpoint.get("ts"),
                        parent_config=tup.parent_config,
                    )
                )
            return out
        return self.list_history(config, limit=limit)

    def delta_channel_history(
        self,
        config: Dict[str, Any],
        *,
        channels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not hasattr(self.backend, "get_delta_channel_history"):
            return {}
        chans = channels or []
        return dict(self.backend.get_delta_channel_history(config=config, channels=chans))

    async def adelta_channel_history(
        self,
        config: Dict[str, Any],
        *,
        channels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if hasattr(self.backend, "aget_delta_channel_history"):
            chans = channels or []
            return dict(await self.backend.aget_delta_channel_history(config=config, channels=chans))
        return self.delta_channel_history(config, channels=channels)


def json_file_checkpointer(root: str = ".chorusgraph/checkpoints") -> EngineCheckpointer:
    from prismlang import JsonFileCheckpointer

    from chorusgraph.core.pending_writes import PendingWriteStore

    return EngineCheckpointer(JsonFileCheckpointer(root), _pending=PendingWriteStore(root))


def async_json_file_checkpointer(root: str = ".chorusgraph/checkpoints") -> EngineCheckpointer:
    from prismlang import AsyncJsonFileCheckpointer

    return EngineCheckpointer(AsyncJsonFileCheckpointer(root))


def postgres_checkpointer(
    conn_string: str,
    *,
    pending_writes_root: str | None = None,
) -> EngineCheckpointer:
    """Postgres-backed checkpointer (P2 mandate) — requires ``CHORUSGRAPH_PG_DSN`` at runtime."""
    from prismlang import AsyncPostgresCheckpointer

    backend = AsyncPostgresCheckpointer(conn_string)
    pending = pending_store_for_backend(backend, root=pending_writes_root)
    return EngineCheckpointer(backend, _pending=pending)


__all__ = [
    "EngineCheckpointer",
    "GraphStateSnapshot",
    "async_json_file_checkpointer",
    "json_file_checkpointer",
    "metadata_for_step",
    "postgres_checkpointer",
    "state_from_checkpoint",
    "state_to_checkpoint",
]
