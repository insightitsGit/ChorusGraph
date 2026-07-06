"""ChorusGraph sidecar metadata for PrismCache entries (384-d + taxonomy + profile)."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

import numpy as np

from chorusgraph.cache_gate.scope import normalize_exact_query


@dataclass(frozen=True)
class SidecarEntry:
    packet_id: str
    raw_embedding_384: np.ndarray
    category_slug: str
    cache_policy: str
    canonical_query: str
    scope_id: str = "global"
    keying: str = "semantic"
    fingerprint_key: str = ""
    valid_from: float = 0.0
    valid_until: Optional[float] = None


class SidecarStore:
    """
    ChorusGraph-owned metadata keyed by PrismCache packet_id.

    Extended for H21: scope, TTL, keying mode, fingerprint index.
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
                canonical_query TEXT NOT NULL,
                scope_id TEXT NOT NULL DEFAULT 'global',
                keying TEXT NOT NULL DEFAULT 'semantic',
                fingerprint_key TEXT NOT NULL DEFAULT '',
                valid_from REAL NOT NULL DEFAULT 0,
                valid_until REAL
            )
            """
        )
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sidecar_lookup
            ON cache_sidecar (scope_id, category_slug, keying, fingerprint_key)
            """
        )
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sidecar_exact
            ON cache_sidecar (scope_id, category_slug, canonical_query)
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
        scope_id: str = "global",
        keying: str = "semantic",
        fingerprint_key: str = "",
        valid_from: Optional[float] = None,
        valid_until: Optional[float] = None,
    ) -> None:
        blob = raw_embedding.astype(np.float32).tobytes()
        vf = float(valid_from if valid_from is not None else time.time())
        self._conn.execute(
            """
            INSERT OR REPLACE INTO cache_sidecar
                (packet_id, raw_embedding, category_slug, cache_policy, canonical_query,
                 scope_id, keying, fingerprint_key, valid_from, valid_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                packet_id,
                blob,
                category_slug,
                cache_policy,
                canonical_query,
                scope_id,
                keying,
                fingerprint_key or "",
                vf,
                valid_until,
            ),
        )
        self._conn.commit()

    def get(self, packet_id: str) -> Optional[SidecarEntry]:
        row = self._conn.execute(
            """
            SELECT packet_id, raw_embedding, category_slug, cache_policy, canonical_query,
                   scope_id, keying, fingerprint_key, valid_from, valid_until
            FROM cache_sidecar WHERE packet_id = ?
            """,
            (packet_id,),
        ).fetchone()
        if row is None:
            return None
        (
            pid,
            blob,
            slug,
            policy,
            query,
            scope_id,
            keying,
            fp_key,
            valid_from,
            valid_until,
        ) = row
        vec = np.frombuffer(blob, dtype=np.float32)
        return SidecarEntry(
            packet_id=pid,
            raw_embedding_384=vec,
            category_slug=slug,
            cache_policy=policy,
            canonical_query=query,
            scope_id=scope_id or "global",
            keying=keying or "semantic",
            fingerprint_key=fp_key or "",
            valid_from=float(valid_from or 0),
            valid_until=float(valid_until) if valid_until is not None else None,
        )

    def is_expired(self, entry: SidecarEntry, *, now: float) -> bool:
        if entry.valid_until is None:
            return False
        return now >= entry.valid_until

    def find_by_fingerprint(
        self,
        *,
        scope_id: str,
        category_slug: str,
        fingerprint_key: str,
        now: float,
    ) -> Optional[SidecarEntry]:
        row = self._conn.execute(
            """
            SELECT packet_id FROM cache_sidecar
            WHERE scope_id = ? AND category_slug = ? AND keying = 'fingerprint'
              AND fingerprint_key = ?
            ORDER BY valid_from DESC LIMIT 1
            """,
            (scope_id, category_slug, fingerprint_key),
        ).fetchone()
        if row is None:
            return None
        entry = self.get(row[0])
        if entry is None or self.is_expired(entry, now=now):
            return None
        return entry

    def find_by_exact(
        self,
        *,
        scope_id: str,
        category_slug: str,
        query: str,
        now: float,
    ) -> Optional[SidecarEntry]:
        normalized = normalize_exact_query(query)
        row = self._conn.execute(
            """
            SELECT packet_id FROM cache_sidecar
            WHERE scope_id = ? AND category_slug = ? AND keying = 'exact'
              AND canonical_query = ?
            ORDER BY valid_from DESC LIMIT 1
            """,
            (scope_id, category_slug, normalized),
        ).fetchone()
        if row is None:
            return None
        entry = self.get(row[0])
        if entry is None or self.is_expired(entry, now=now):
            return None
        return entry

    def list_in_scope(self, scope_id: str, *, category_slug: Optional[str] = None) -> List[SidecarEntry]:
        if category_slug:
            rows = self._conn.execute(
                "SELECT packet_id FROM cache_sidecar WHERE scope_id = ? AND category_slug = ?",
                (scope_id, category_slug),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT packet_id FROM cache_sidecar WHERE scope_id = ?",
                (scope_id,),
            ).fetchall()
        out: List[SidecarEntry] = []
        for (pid,) in rows:
            e = self.get(pid)
            if e:
                out.append(e)
        return out

    def close(self) -> None:
        self._conn.close()


__all__ = ["SidecarEntry", "SidecarStore"]
