"""SQLite-backed GraphStore — survives process restart (E5)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from prismcortex.adapters.reference import InMemoryGraphStore
from prismcortex.models import Edge, Node

from chorusgraph.persistence.migrations import migrate


class SqliteGraphStore:
    """
    Durable GraphStore wrapping InMemoryGraphStore with SQLite persistence.

    Implements the prismcortex GraphStore protocol; graph state survives restart.
    """

    def __init__(self, db_path: str | Path, *, tenant_id: str = "default", store_key: str = "cortex") -> None:
        self._db_path = Path(db_path)
        self._tenant_id = tenant_id
        self._store_key = store_key
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._inner = InMemoryGraphStore()
        self._conn = sqlite3.connect(str(self._db_path))
        migrate(self._conn)
        self._load()

    def close(self) -> None:
        self._conn.close()

    def _load(self) -> None:
        row = self._conn.execute(
            "SELECT nodes_json, edges_json, version FROM cortex_graph_state "
            "WHERE tenant_id = ? AND store_key = ?",
            (self._tenant_id, self._store_key),
        ).fetchone()
        if not row:
            return
        nodes_data = json.loads(row[0] or "{}")
        edges_data = json.loads(row[1] or "{}")
        self._inner._nodes = {k: Node.model_validate(v) for k, v in nodes_data.items()}
        self._inner._edges = {k: Edge.model_validate(v) for k, v in edges_data.items()}
        self._inner._version = int(row[2] or 0)
        self._inner._label_index = {}
        for nid, node in self._inner._nodes.items():
            key = node.label.strip().lower()
            self._inner._label_index[key] = nid
        self._inner._matrix_dirty = True

    def _save(self) -> None:
        nodes_json = json.dumps({k: v.model_dump(mode="json") for k, v in self._inner._nodes.items()})
        edges_json = json.dumps({k: v.model_dump(mode="json") for k, v in self._inner._edges.items()})
        tombstones_json = json.dumps(list(self._inner._tombstones))
        self._conn.execute(
            """
            INSERT INTO cortex_graph_state (tenant_id, store_key, version, nodes_json, edges_json, tombstones_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_id, store_key) DO UPDATE SET
                version = excluded.version,
                nodes_json = excluded.nodes_json,
                edges_json = excluded.edges_json,
                tombstones_json = excluded.tombstones_json,
                updated_at = datetime('now')
            """,
            (
                self._tenant_id,
                self._store_key,
                self._inner._version,
                nodes_json,
                edges_json,
                tombstones_json,
            ),
        )
        self._conn.commit()

    def node_count(self) -> int:
        return len(self._inner._nodes)

    def edge_count(self) -> int:
        return len(self._inner._edges)

    # GraphStore protocol — delegate reads, persist writes
    def find_node_by_label(self, label: str) -> Optional[str]:
        return self._inner.find_node_by_label(label)

    def find_similar_node(self, embedding: list[float], threshold: float = 0.88) -> Optional[str]:
        return self._inner.find_similar_node(embedding, threshold=threshold)

    def current_edge(self, src: str, relation: str):
        return self._inner.current_edge(src, relation)

    def current_edges_from(self, src: str):
        return self._inner.current_edges_from(src)

    def retrieve(self, embedding: list[float], k: int = 8):
        return self._inner.retrieve(embedding, k=k)

    def version(self):
        return self._inner.version()

    def tombstones(self):
        return self._inner.tombstones()

    def apply(self, delta):
        result = self._inner.apply(delta)
        self._save()
        return result

    def prune_to(self, max_current_edges: int) -> int:
        n = self._inner.prune_to(max_current_edges)
        if n:
            self._save()
        return n

    def forget_source(self, source_id: str) -> dict:
        receipt = self._inner.forget_source(source_id)
        self._save()
        return receipt

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)
