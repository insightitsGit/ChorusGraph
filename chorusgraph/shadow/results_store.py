"""Persist shadow-mode per-query outcomes."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class ShadowRow:
    query: str
    slug: str
    cache_policy: str
    coarse_score: float
    verify_score: float
    verify_threshold: float
    decision: str
    equivalent: bool
    verdict: str
    is_hit: bool
    fp_eligible: bool


class ShadowResultsStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shadow_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                slug TEXT NOT NULL,
                cache_policy TEXT NOT NULL,
                coarse_score REAL,
                verify_score REAL,
                verify_threshold REAL NOT NULL,
                decision TEXT NOT NULL,
                equivalent INTEGER NOT NULL,
                verdict TEXT NOT NULL,
                is_hit INTEGER NOT NULL,
                fp_eligible INTEGER NOT NULL
            )
            """
        )
        self._conn.commit()

    def insert(self, row: ShadowRow) -> None:
        self._conn.execute(
            """
            INSERT INTO shadow_results
                (query, slug, cache_policy, coarse_score, verify_score,
                 verify_threshold, decision, equivalent, verdict, is_hit, fp_eligible)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.query,
                row.slug,
                row.cache_policy,
                row.coarse_score,
                row.verify_score,
                row.verify_threshold,
                row.decision,
                int(row.equivalent),
                row.verdict,
                int(row.is_hit),
                int(row.fp_eligible),
            ),
        )
        self._conn.commit()

    def fetch_all(self, verify_threshold: Optional[float] = None) -> List[ShadowRow]:
        if verify_threshold is None:
            rows = self._conn.execute("SELECT * FROM shadow_results ORDER BY id").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM shadow_results WHERE verify_threshold = ? ORDER BY id",
                (verify_threshold,),
            ).fetchall()
        out: list[ShadowRow] = []
        for r in rows:
            _id, query, slug, policy, coarse, verify, thresh, decision, equiv, verdict, is_hit, fp_elig = r
            out.append(
                ShadowRow(
                    query=query,
                    slug=slug,
                    cache_policy=policy,
                    coarse_score=coarse or 0.0,
                    verify_score=verify or 0.0,
                    verify_threshold=thresh,
                    decision=decision,
                    equivalent=bool(equiv),
                    verdict=verdict,
                    is_hit=bool(is_hit),
                    fp_eligible=bool(fp_elig),
                )
            )
        return out

    def clear(self) -> None:
        self._conn.execute("DELETE FROM shadow_results")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
