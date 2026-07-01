"""Inspect ai_chat tables on insight_hospital."""
from __future__ import annotations

import subprocess

AZ_CMD = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"


def _az(*args: str) -> str:
    return subprocess.check_output([AZ_CMD, *args], text=True).strip()


def main() -> None:
    import psycopg2

    url = _az("keyvault", "secret", "show", "--vault-name", "kvinsightitsprod01", "--name", "database-url", "--query", "value", "-o", "tsv")
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    for table in ("ai_chat_observations", "ai_chat_trace_events"):
        cur.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = %s ORDER BY ordinal_position",
            (table,),
        )
        print(f"\n{table} columns:")
        for col, dtype in cur.fetchall():
            print(f"  {col}: {dtype}")
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  row_count: {cur.fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    main()
