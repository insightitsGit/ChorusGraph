"""Per-node pending write storage — Improve-1 T1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from chorusgraph.core.channels import NodeUpdate


class MidStepAbort(Exception):
    """Raised when a node fails mid super-step; pending writes enable partial resume."""

    def __init__(self, state: Dict[str, Any], *, super_step: int, active_nodes: set[str]) -> None:
        self.state = state
        self.super_step = super_step
        self.active_nodes = active_nodes
        super().__init__(f"Mid-step abort at super_step={super_step} nodes={sorted(active_nodes)}")


def node_update_to_dict(update: NodeUpdate) -> Dict[str, Any]:
    return {
        "envelopes": list(update.envelopes),
        "artifacts": dict(update.artifacts),
        "rule_chain": list(update.rule_chain),
    }


def node_update_from_dict(data: Dict[str, Any]) -> NodeUpdate:
    return NodeUpdate(
        envelopes=list(data.get("envelopes") or []),
        artifacts=dict(data.get("artifacts") or {}),
        rule_chain=list(data.get("rule_chain") or []),
    )


def _thread_id_from_config(config: Dict[str, Any]) -> str:
    return str(config.get("configurable", {}).get("thread_id") or "default")


class PendingWriteStore:
    """
    ChorusGraph-owned pending writes under the checkpoint root.

    prismlang ``put_writes`` is currently a no-op on JsonFileCheckpointer;
    this store is authoritative for local resume.
    """

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root) / "pending_writes"

    def _step_dir(self, thread_id: str, super_step: int) -> Path:
        safe = thread_id.replace("/", "_").replace("\\", "_")
        return self._root / safe / str(super_step)

    def put(self, config: Dict[str, Any], super_step: int, node_id: str, update: NodeUpdate) -> None:
        step_dir = self._step_dir(_thread_id_from_config(config), super_step)
        step_dir.mkdir(parents=True, exist_ok=True)
        path = step_dir / f"{node_id}.json"
        path.write_text(json.dumps(node_update_to_dict(update), ensure_ascii=False), encoding="utf-8")

    def list_for_step(self, config: Dict[str, Any], super_step: int) -> Dict[str, NodeUpdate]:
        step_dir = self._step_dir(_thread_id_from_config(config), super_step)
        if not step_dir.is_dir():
            return {}
        out: Dict[str, NodeUpdate] = {}
        for path in sorted(step_dir.glob("*.json")):
            node_id = path.stem
            data = json.loads(path.read_text(encoding="utf-8"))
            out[node_id] = node_update_from_dict(data)
        return out

    def clear_step(self, config: Dict[str, Any], super_step: int) -> None:
        step_dir = self._step_dir(_thread_id_from_config(config), super_step)
        if not step_dir.is_dir():
            return
        for path in step_dir.glob("*.json"):
            path.unlink(missing_ok=True)
        try:
            step_dir.rmdir()
        except OSError:
            pass

    def has_step(self, config: Dict[str, Any], super_step: int) -> bool:
        step_dir = self._step_dir(_thread_id_from_config(config), super_step)
        return step_dir.is_dir() and any(step_dir.glob("*.json"))


def pending_store_for_backend(backend: Any) -> Optional[PendingWriteStore]:
    root = getattr(backend, "root", None)
    if root is None:
        return None
    return PendingWriteStore(root)


__all__ = [
    "MidStepAbort",
    "PendingWriteStore",
    "node_update_from_dict",
    "node_update_to_dict",
    "pending_store_for_backend",
]
