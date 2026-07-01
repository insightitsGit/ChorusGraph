"""Debug one chunk fetch from VM."""
from __future__ import annotations

import base64
import json
import subprocess
import tempfile
from pathlib import Path

AZ_CMD = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
DBG = Path(__file__).resolve().parent / "_chunk_debug.txt"

script = """#!/bin/bash
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
    OFFSET 0 LIMIT 2
  ) t
) TO STDOUT
" | base64 -w 0
"""

with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False, encoding="utf-8") as tmp:
    tmp.write(script)
    tmp_path = tmp.name

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
Path(tmp_path).unlink(missing_ok=True)
DBG.write_text(raw, encoding="utf-8")
message = json.loads(raw)["value"][0]["message"]
stdout = message.split("[stdout]", 1)[1].split("[stderr]", 1)[0].strip()
print("stdout_len", len(stdout))
print("stdout_head", stdout[:80])
try:
    text = base64.b64decode("".join(stdout.split())).decode("utf-8")
    print("decoded_len", len(text))
    print("decoded_head", repr(text[:200]))
    import re
    parts = re.split(r"(?<=\})(?=\{)", text.strip())
    print("parts", len(parts))
    for p in parts:
        print(" query:", json.loads(p)["query"][:50])
except Exception as e:
    print("decode_err", e)
