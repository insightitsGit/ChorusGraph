"""Export website_chat_turns using Azure Key Vault database-url."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

OUTPUT = Path(__file__).resolve().parents[1] / "chorusgraph" / "shadow" / "replay" / "data" / "website_chat_turns.jsonl"
AZ_CMD = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
VAULT = "kvinsightitsprod01"

SQL = """
SELECT user_message AS query,
       COALESCE(NULLIF(route, ''), 'general') AS category_slug,
       assistant_message AS response,
       created_at AS timestamp,
       id AS section_id
FROM website_chat_turns
WHERE assistant_message IS NOT NULL AND assistant_message <> ''
ORDER BY created_at ASC
"""


def _az(*args: str) -> str:
    return subprocess.check_output([AZ_CMD, *args], text=True).strip()


def _get_database_url() -> str:
    return _az("keyvault", "secret", "show", "--vault-name", VAULT, "--name", "database-url", "--query", "value", "-o", "tsv")


def main() -> int:
    try:
        import psycopg2
    except ImportError:
        print("pip install psycopg2-binary", file=sys.stderr)
        return 1

    url = _get_database_url()
    parsed = urlparse(url)
    print(f"Connecting to host={parsed.hostname} db={parsed.path.lstrip('/')}", file=sys.stderr)

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
        ("website_chat_turns",),
    )
    if cur.fetchone()[0] == 0:
        print("website_chat_turns not found", file=sys.stderr)
        return 2

    cur.execute(SQL)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with OUTPUT.open("w", encoding="utf-8") as out:
        for row in cur:
            query, slug, response, ts, section_id = row
            record = {
                "query": query,
                "category_slug": slug or "general",
                "response": response,
                "timestamp": ts if isinstance(ts, str) else ts.isoformat(),
                "section_id": section_id,
            }
            out.write(json.dumps(record, ensure_ascii=True) + "\n")
            count += 1
    conn.close()
    print(f"Exported {count} turns to {OUTPUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
