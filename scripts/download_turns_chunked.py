"""Download website_chat_turns JSONL from prod VM in chunks (COPY + robust JSON parse)."""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

AZ_CMD = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
OUTPUT = Path(__file__).resolve().parents[1] / "chorusgraph" / "shadow" / "replay" / "data" / "website_chat_turns.jsonl"
CHUNK = 1


def _make_script(offset: int, limit: int) -> str:
    return f"""#!/bin/bash
set -e
docker exec postgres psql -U meeting_user -d meeting_scheduler -t -A -c "
COPY (
  SELECT row_to_json(t)
  FROM (
    SELECT user_message AS query,
           COALESCE(NULLIF(route,''), 'general') AS category_slug,
           assistant_message AS response,
           created_at AS timestamp,
           id AS section_id
    FROM website_chat_turns
    WHERE assistant_message IS NOT NULL AND assistant_message <> ''
    ORDER BY created_at ASC
    OFFSET {offset} LIMIT {limit}
  ) t
) TO STDOUT
" | base64 -w 0
"""


def _split_json_objects(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if text.count("{") == 1:
        return [text]
    parts = re.split(r"(?<=\})(?=\{)", text)
    return [p.strip() for p in parts if p.strip()]


def _fetch_chunk(offset: int, limit: int) -> list[str]:
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False, encoding="utf-8") as tmp:
        tmp.write(_make_script(offset, limit))
        tmp_path = tmp.name
    try:
        raw = subprocess.check_output(
            [
                AZ_CMD,
                "vm",
                "run-command",
                "invoke",
                "--resource-group",
                "RG-INSIGHTITS-PROD",
                "--name",
                "vm-insightits-prod",
                "--command-id",
                "RunShellScript",
                "--scripts",
                f"@{tmp_path}",
                "-o",
                "json",
            ],
            text=True,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    payload = json.loads(raw)
    message = payload["value"][0]["message"]
    stdout = message.split("[stdout]", 1)[1] if "[stdout]" in message else message
    if "[stderr]" in stdout:
        stdout = stdout.split("[stderr]", 1)[0]
    b64 = "".join(stdout.split())
    if not b64:
        return []
    text = base64.b64decode(b64).decode("utf-8", errors="replace")
    lines: list[str] = []
    for blob in text.splitlines():
        blob = blob.strip()
        if not blob:
            continue
        try:
            json.loads(blob)
            lines.append(blob)
            continue
        except json.JSONDecodeError:
            pass
        for obj in _split_json_objects(blob):
            json.loads(obj)
            lines.append(obj)
    return lines


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    records: list[str] = []
    offset = 0
    empty = 0
    while empty < 2:
        try:
            chunk = _fetch_chunk(offset, CHUNK)
        except Exception as exc:
            print(f"offset={offset} error: {exc}", file=sys.stderr)
            chunk = []
        if not chunk:
            empty += 1
        else:
            empty = 0
            records.extend(chunk)
            print(f"offset={offset} got {len(chunk)} (total {len(records)})", file=sys.stderr)
        offset += CHUNK

    # dedupe by section_id
    seen: set[str] = set()
    unique: list[str] = []
    for line in records:
        sid = json.loads(line).get("section_id")
        if sid in seen:
            continue
        seen.add(sid)
        unique.append(line)

    with OUTPUT.open("w", encoding="utf-8") as out:
        for line in unique:
            out.write(line + "\n")
    print(f"Wrote {len(unique)} records to {OUTPUT}", file=sys.stderr)
    return 0 if unique else 1


if __name__ == "__main__":
    raise SystemExit(main())
