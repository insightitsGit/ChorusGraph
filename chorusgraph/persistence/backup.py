"""Backup and restore for ChorusGraph SQLite stores (E5)."""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass
class BackupManifest:
    files: List[Path]
    backup_dir: Path


def backup_sqlite_stores(
    *,
    target_dir: str | Path,
    sources: Iterable[str | Path],
) -> BackupManifest:
    """Copy SQLite database files to a timestamped backup directory."""
    import datetime as dt

    root = Path(target_dir)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = root / f"backup_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    copied: List[Path] = []
    for src in sources:
        path = Path(src)
        if not path.exists():
            continue
        dest = out / path.name
        shutil.copy2(path, dest)
        copied.append(dest)
    return BackupManifest(files=copied, backup_dir=out)


def restore_sqlite_store(backup_file: str | Path, target: str | Path) -> Path:
    """Restore a single SQLite file from backup."""
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_file, target_path)
    # Verify readable
    conn = sqlite3.connect(str(target_path))
    conn.execute("SELECT 1")
    conn.close()
    return target_path


def verify_backup_integrity(backup_dir: str | Path) -> bool:
    """Ensure every .db in backup dir opens cleanly."""
    root = Path(backup_dir)
    dbs = list(root.glob("*.db"))
    if not dbs:
        return False
    for db in dbs:
        conn = sqlite3.connect(str(db))
        conn.execute("SELECT 1")
        conn.close()
    return True
