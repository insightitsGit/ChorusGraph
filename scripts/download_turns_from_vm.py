"""Download website_chat_turns JSONL from prod VM via az run-command."""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from pathlib import Path

AZ_CMD = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
SCRIPT = Path(__file__).resolve().parent / "vm_export_turns_b64.sh"
OUTPUT = Path(__file__).resolve().parents[1] / "chorusgraph" / "shadow" / "replay" / "data" / "website_chat_turns.jsonl"


def main() -> int:
    print("Exporting from vm-insightits-prod...", file=sys.stderr)
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
            f"@{SCRIPT}",
            "-o",
            "json",
        ],
        text=True,
    )
    payload = json.loads(raw)
    message = payload["value"][0]["message"]
    if "[stdout]" in message:
        stdout = message.split("[stdout]", 1)[1]
        if "[stderr]" in stdout:
            stdout = stdout.split("[stderr]", 1)[0]
    else:
        stdout = message
    stdout = stdout.strip()
    # drop optional wc -c line
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    if lines and lines[0].isdigit():
        lines = lines[1:]
    b64 = "".join(lines)
    data = base64.b64decode(b64)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(data)
    count = sum(1 for _ in OUTPUT.open(encoding="utf-8"))
    print(f"Wrote {count} records to {OUTPUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
