"""Postgres-backed GraphStore — multi-replica concurrent-writer safety (Enterprise)."""

from __future__ import annotations

import json
from typing import Any, Callable, Optional, TypeVar

from prismcortex.adapters.reference import InMemoryGraphStore
from prismcortex.models import Edge, Node

from chorusgraph.licensing import ENTERPRISE_PERSISTENCE, require_feature
from chorusgraph.persistence.postgres_migrations import migrate

T = TypeVar("T")


class PostgresGraphStore:
    """
    Durable GraphStore with transactional advisory locking for concurrent writers.

    Requires ``CHORUSGRAPH_LICENSE_FILE`` with ``enterprise_persistence`` entitlement.
    """

    def __init__(
        self,
        dsn: str,
        *,
        tenant_id: str = "default",
        store_key: str = "cortex",
    ) -> None:
        require_feature(ENTERPRISE_PERSISTENCE)
        try:
            import psycopg
        except ImportError as exc:
            raise ImportError(
                "PostgresGraphStore requires psycopg. Install: pip install 'chorusgraph[postgres]'"
            ) from exc
        self._dsn = dsn
        self._tenant_id = tenant_id
        self._store_key = store_key
        self._conn = psycopg.connect(dsn, autocommit=False)
        self._inner = InMemoryGraphStore()
        migrate(self._conn)
        self._conn.commit()
        self._load()

    def close(self) -> None:
        self._conn.close()

    def _hydrate_from_row(self, row: tuple | None) -> None:
        if not row:
            self._inner = InMemoryGraphStore()
            return
        nodes_data = row[0] if isinstance(row[0], dict) else json.loads(row[0] or "{}")
        edges_data = row[1] if isinstance(row[1], dict) else json.loads(row[1] or "{}")
        self._inner._nodes = {k: Node.model_validate(v) for k, v in nodes_data.items()}
        self._inner._edges = {k: Edge.model_validate(v) for k, v in edges_data.items()}
        self._inner._version = int(row[2] or 0)
        self._inner._label_index = {}
        for nid, node in self._inner._nodes.items():
            key = node.label.strip().lower()
            self._inner._label_index[key] = nid
        self._inner._matrix_dirty = True

    def _advisory_lock(self) -> None:
        self._conn.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            (f"{self._tenant_id}:{self._store_key}",),
        )

    def _fetch_row(self):
        return self._conn.execute(
            """
            SELECT nodes_json, edges_json, version
            FROM cortex_graph_state
            WHERE tenant_id = %s AND store_key = %s
            """,
            (self._tenant_id, self._store_key),
        ).fetchone()

    def _write_row(self) -> None:
        nodes_json = json.dumps({k: v.model_dump(mode="json") for k, v in self._inner._nodes.items()})
        edges_json = json.dumps({k: v.model_dump(mode="json") for k, v in self._inner._edges.items()})
        tombstones_json = json.dumps(list(self._inner._tombstones))
        self._conn.execute(
            """
            INSERT INTO cortex_graph_state
                (tenant_id, store_key, version, nodes_json, edges_json, tombstones_json)
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
            ON CONFLICT (tenant_id, store_key) DO UPDATE SET
                version = EXCLUDED.version,
                nodes_json = EXCLUDED.nodes_json,
                edges_json = EXCLUDED.edges_json,
                tombstones_json = EXCLUDED.tombstones_json,
                updated_at = NOW()
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

    def _mutate(self, fn: Callable[[], T]) -> T:
        with self._conn.transaction():
            self._advisory_lock()
            self._hydrate_from_row(self._fetch_row())
            result = fn()
            self._write_row()
            return result

    def _load(self) -> None:
        self._hydrate_from_row(self._fetch_row())

    def node_count(self) -> int:
        return len(self._inner._nodes)

    def edge_count(self) -> int:
        return len(self._inner._edges)

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
        return self._mutate(lambda: self._inner.apply(delta))

    def prune_to(self, max_current_edges: int) -> int:
        return self._mutate(lambda: self._inner.prune_to(max_current_edges))

    def forget_source(self, source_id: str) -> dict:
        return self._mutate(lambda: self._inner.forget_source(source_id))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)
