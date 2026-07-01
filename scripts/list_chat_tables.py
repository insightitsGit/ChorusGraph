"""List databases and chat-related tables on production Postgres."""
from __future__ import annotations

import subprocess
import sys

AZ_CMD = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
VAULT = "kvinsightitsprod01"


def _az(*args: str) -> str:
    return subprocess.check_output([AZ_CMD, *args], text=True).strip()


def main() -> None:
    import psycopg2

    url = _az("keyvault", "secret", "show", "--vault-name", VAULT, "--name", "database-url", "--query", "value", "-o", "tsv")
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name LIKE %s ORDER BY table_name",
        ("%chat%",),
    )
    print("chat_tables_insight_hospital:", [r[0] for r in cur.fetchall()])
    conn.close()

    # try meeting_scheduler db on same host
    from urllib.parse import urlparse, urlunparse
    p = urlparse(url)
    ms_url = urlunparse(p._replace(path="/meeting_scheduler"))
    try:
        conn2 = psycopg2.connect(ms_url)
        cur2 = conn2.cursor()
        cur2.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name LIKE %s ORDER BY table_name",
            ("%chat%",),
        )
        print("chat_tables_meeting_scheduler:", [r[0] for r in cur2.fetchall()])
        cur2.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
            ("website_chat_turns",),
        )
        if cur2.fetchone()[0]:
            cur2.execute(
                "SELECT COUNT(*) FROM website_chat_turns "
                "WHERE assistant_message IS NOT NULL AND assistant_message <> %s",
                ("",),
            )
            print("website_chat_turns_count", cur2.fetchone()[0])
        conn2.close()
    except Exception as e:
        print("meeting_scheduler_error", type(e).__name__, str(e)[:120])


if __name__ == "__main__":
    main()
