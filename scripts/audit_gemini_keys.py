"""Audit Gemini key sources — suffix only, never print full secrets."""

from __future__ import annotations

import os
import sys
from pathlib import Path

KEY_NAMES = {
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY_NEW",
    "GEMINI_API_KEY_BENCHMARK",
    "GEMINI_API_KEY_DEFAULT",
}

PATHS = [
    Path(__file__).resolve().parents[1] / ".env",
    Path(r"c:\code\InsightitsAIAgent\meeting-scheduler\db_connection.local.env"),
    Path(r"c:\code\InsightitsAIAgent\meeting-scheduler\.env"),
    Path(r"c:\code\PrismCortex\.env"),
    Path(r"c:\code\InsightMappingRag\.env"),
]


def collect() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for name in KEY_NAMES:
        val = os.environ.get(name)
        if val and val.strip() not in ("", "CHANGE_ME_GEMINI_KEY"):
            found.setdefault(val.strip(), []).append(f"env:{name}")
    for path in PATHS:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, val = line.split("=", 1)
            name = name.strip()
            val = val.strip().strip('"').strip("'")
            if name in KEY_NAMES and val and val != "CHANGE_ME_GEMINI_KEY":
                found.setdefault(val, []).append(str(path))
    return found


def main() -> int:
    keys = collect()
    print(f"Found {len(keys)} unique key(s):\n")
    for key, sources in keys.items():
        suffix = key[-4:] if len(key) >= 4 else "****"
        print(f"  ...{suffix}  len={len(key)}  ends_with_p0={key.endswith('p0')}")
        for src in sources:
            print(f"    - {src}")
    print()
    from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key

    active = resolve_gemini_api_key()
    if active:
        print(
            f"resolve_gemini_api_key() active suffix: ...{active[-4:]}  "
            f"ends_with_p0={active.endswith('p0')}"
        )
    else:
        print("resolve_gemini_api_key(): none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
