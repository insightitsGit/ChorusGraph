"""Probe hub Postgres for website_chat_turns (no secrets printed)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

MEETING = Path(r"c:\code\InsightitsAIAgent\meeting-scheduler")
sys.path.insert(0, str(MEETING))

for name in (".env", "db_connection.env", "db_connection.local.env", ".env.local", "env.local"):
    path = MEETING / name
    if not path.exists():
        continue
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

url = os.environ.get("DATABASE_URL", "")
if not url and os.environ.get("DB_HOST"):
    user = os.environ.get("DB_USER", "meeting_user")
    password = os.environ.get("DB_PASSWORD", "")
    host = os.environ["DB_HOST"]
    port = os.environ.get("DB_PORT", "5432")
    db = os.environ.get("DB_NAME", "meeting_scheduler")
    if password:
        url = f"postgresql://{user}:{password}@{host}:{port}/{db}"

print("has_url", bool(url))
if url:
    # redacted host only
    host_part = url.split("@")[-1].split("/")[0] if "@" in url else "unknown"
    print("host_part", host_part)

try:
    import psycopg2
except ImportError:
    print("psycopg2_missing")
    sys.exit(1)

if not url:
    print("no_connection_config")
    sys.exit(0)

try:
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
        ("website_chat_turns",),
    )
    exists = cur.fetchone()[0]
    print("table_exists", exists)
    if exists:
        cur.execute(
            "SELECT COUNT(*) FROM website_chat_turns "
            "WHERE assistant_message IS NOT NULL AND assistant_message <> %s",
            ("",),
        )
        print("turn_count", cur.fetchone()[0])
    conn.close()
except Exception as e:
    print("connect_error", type(e).__name__, str(e)[:200])
