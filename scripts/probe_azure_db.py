"""Try Azure Postgres connection using meeting-scheduler db_connection env files."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

MEETING = Path(r"c:\code\InsightitsAIAgent\meeting-scheduler")
for name in ("db_connection.local.env", "db_connection.env", ".env.local", ".env"):
    path = MEETING / name
    if not path.exists():
        continue
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import psycopg2

host = os.environ.get("DB_HOST", "")
db = os.environ.get("DB_NAME", "")
user = os.environ.get("DB_USER", "")
has_pw = bool(os.environ.get("DB_PASSWORD", ""))
print("host_set", bool(host), "db", db, "user", user, "has_password", has_pw)

if not (host and user and has_pw):
    print("missing_creds")
    sys.exit(1)

try:
    conn = psycopg2.connect(
        host=host,
        dbname=db,
        user=user,
        password=os.environ["DB_PASSWORD"],
        port=int(os.environ.get("DB_PORT", "5432")),
        sslmode=os.environ.get("DB_SSLMODE", "require"),
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
