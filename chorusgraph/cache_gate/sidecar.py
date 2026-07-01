"""ChorusGraph sidecar metadata for PrismCache entries (384-d + taxonomy)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class SidecarEntry:
    packet_id: str
    raw_embedding_384: np.ndarray
    category_slug: str
    cache_policy: str
    canonical_query: str


class SidecarStore:
    """
    ChorusGraph-owned metadata keyed by PrismCache packet_id.

    PrismCache does not persist raw 384-d embeddings or category_slug; we store
    them here at seed/write time for Stage-2 verify and taxonomy guard replay.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_sidecar (
                packet_id TEXT PRIMARY KEY,
                raw_embedding BLOB NOT NULL,
                category_slug TEXT NOT NULL,
                cache_policy TEXT NOT NULL,
                canonical_query TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def put(
        self,
        packet_id: str,
        *,
        raw_embedding: np.ndarray,
        category_slug: str,
        cache_policy: str,
        canonical_query: str,
    ) -> None:
        blob = raw_embedding.astype(np.float32).tobytes()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO cache_sidecar
                (packet_id, raw_embedding, category_slug, cache_policy, canonical_query)
            VALUES (?, ?, ?, ?, ?)
            """,
            (packet_id, blob, category_slug, cache_policy, canonical_query),
        )
        self._conn.commit()

    def get(self, packet_id: str) -> Optional[SidecarEntry]:
        row = self._conn.execute(
            "SELECT packet_id, raw_embedding, category_slug, cache_policy, canonical_query "
            "FROM cache_sidecar WHERE packet_id = ?",
            (packet_id,),
        ).fetchone()
        if row is None:
            return None
        pid, blob, slug, policy, query = row
        vec = np.frombuffer(blob, dtype=np.float32)
        return SidecarEntry(
            packet_id=pid,
            raw_embedding_384=vec,
            category_slug=slug,
            cache_policy=policy,
            canonical_query=query,
        )

    def close(self) -> None:
        self._conn.close()
