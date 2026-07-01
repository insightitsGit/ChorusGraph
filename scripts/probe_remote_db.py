"""Probe remote EC2 Postgres for website_chat_turns."""
from __future__ import annotations

import os
from pathlib import Path

MEETING = Path(r"c:\code\InsightitsAIAgent\meeting-scheduler")
path = MEETING / "db_connection.env"
if path.exists():
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")

import psycopg2

host = os.environ.get("DB_HOST")
print("host", host)
try:
    conn = psycopg2.connect(
        host=host,
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=int(os.environ.get("DB_PORT", "5432")),
        sslmode="prefer",
        connect_timeout=20,
    )
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
        ("website_chat_turns",),
    )
    print("table_exists", cur.fetchone()[0])
    cur.execute(
        "SELECT COUNT(*) FROM website_chat_turns "
        "WHERE assistant_message IS NOT NULL AND assistant_message <> %s",
        ("",),
    )
    print("turn_count", cur.fetchone()[0])
    conn.close()
except Exception as e:
    print("error", type(e).__name__, str(e)[:200])
