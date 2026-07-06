"""LangGraph checkpoint import CLI — T8."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterator, Tuple

from chorusgraph.core.persistence import json_file_checkpointer
from chorusgraph.core.subgraph import namespaced_thread_id


def _iter_sqlite_checkpoints(db_path: Path) -> Iterator[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "checkpoints" not in tables:
            return
        for row in conn.execute("SELECT thread_id, checkpoint, metadata FROM checkpoints"):
            thread_id = str(row["thread_id"])
            checkpoint = json.loads(row["checkpoint"]) if isinstance(row["checkpoint"], str) else row["checkpoint"]
            metadata = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {})
            yield thread_id, checkpoint, metadata
    finally:
        conn.close()


def import_checkpoints(
    *,
    source_sqlite: Path,
    dest_root: Path,
    namespace_prefix: str = "",
) -> int:
    from uuid import uuid4

    from chorusgraph.core.channels import ChannelState
    from chorusgraph.core.persistence import EngineCheckpointer

    cp = json_file_checkpointer(str(dest_root))
    engine = cp if hasattr(cp, "put") else EngineCheckpointer(cp)
    count = 0
    for thread_id, checkpoint, metadata in _iter_sqlite_checkpoints(source_sqlite):
        mapped_thread = namespaced_thread_id(namespace_prefix, thread_id) if namespace_prefix else thread_id
        config = {"configurable": {"thread_id": mapped_thread}}
        channel_values = checkpoint.get("channel_values") or checkpoint
        state = ChannelState.from_checkpoint_values(channel_values)
        engine.put(
            config,
            state,
            super_step=int(metadata.get("step") or 0),
            active=set(metadata.get("active_nodes") or []),
            graph_id=str(metadata.get("graph_id") or "imported"),
            tenant_id=str(metadata.get("tenant_id") or "default"),
        )
        count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import LangGraph SQLite checkpoints into ChorusGraph threads")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--dest", required=True, type=Path)
    parser.add_argument("--namespace", default="", help="Optional parent thread prefix (T4 namespacing)")
    args = parser.parse_args(argv)
    args.dest.mkdir(parents=True, exist_ok=True)
    n = import_checkpoints(source_sqlite=args.source, dest_root=args.dest, namespace_prefix=args.namespace)
    print(json.dumps({"imported": n, "dest": str(args.dest)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
