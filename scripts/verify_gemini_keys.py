"""Verify Gemini API keys — prints status only, never full secrets."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _mask(key: str) -> str:
    key = key.strip()
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


def _collect_keys() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for name in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY_NEW",
        "GEMINI_API_KEY_BENCHMARK",
        "GEMINI_API_KEY_DEFAULT",
    ):
        val = os.environ.get(name)
        if val and val.strip() not in ("", "CHANGE_ME_GEMINI_KEY"):
            found.append((f"env:{name}", val.strip()))

    _KEY_NAMES = {
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY_NEW",
        "GEMINI_API_KEY_BENCHMARK",
        "GEMINI_API_KEY_DEFAULT",
    }

    paths = [
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[1] / ".env.local",
        Path(r"c:\code\InsightitsAIAgent\meeting-scheduler\.env"),
        Path(r"c:\code\InsightitsAIAgent\meeting-scheduler\db_connection.local.env"),
        Path(r"c:\code\PrismCortex\.env"),
        Path(r"c:\code\InsightMappingRag\.env"),
    ]
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, val = line.split("=", 1)
            name = name.strip()
            val = val.strip().strip('"').strip("'")
            if name not in _KEY_NAMES:
                continue
            if not val or val == "CHANGE_ME_GEMINI_KEY":
                continue
            found.append((f"{path.name}:{name}", val))
    return found


def _probe(key: str, *, model: str = "gemini-2.5-flash") -> dict:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return {"ok": False, "error": "google-genai not installed"}

    client = genai.Client(api_key=key)
    try:
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: ok",
            config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=16),
        )
        text = (response.text or "").strip()
        return {"ok": True, "sample": text[:40]}
    except Exception as exc:
        msg = str(exc)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            return {"ok": False, "error": "QUOTA_EXHAUSTED", "detail": msg[:200]}
        if "401" in msg or "403" in msg or "API key not valid" in msg:
            return {"ok": False, "error": "INVALID_KEY", "detail": msg[:200]}
        return {"ok": False, "error": type(exc).__name__, "detail": msg[:200]}


def main() -> int:
    raw = _collect_keys()
    unique: dict[str, str] = {}
    for label, key in raw:
        unique.setdefault(key, label)

    if not unique:
        print("No Gemini keys found in env or .env files.")
        return 1

    print(f"Found {len(unique)} unique key(s). Probing gemini-2.5-flash...\n")
    p0_keys = [k for k in unique if k.endswith("p0")]
    if p0_keys:
        print(f"  Key(s) ending with 'p0': {len(p0_keys)} (expected new benchmark key)\n")
    else:
        print("  WARNING: no key ending with 'p0' found — add yours to ChorusGraph/.env\n")
    any_ok = False
    for key, first_label in unique.items():
        print(f"  [{_mask(key)}] from {first_label}")
        result = _probe(key)
        if result.get("ok"):
            any_ok = True
            print(f"    STATUS: OK — response={result.get('sample')!r}")
        else:
            print(f"    STATUS: FAIL — {result.get('error')}")
            if result.get("detail"):
                print(f"    detail: {result['detail']}")
        print()

    # What resolve_gemini_api_key would pick (env wins over file setdefault)
    from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key

    active = resolve_gemini_api_key()
    if active:
        for key, label in unique.items():
            if key == active:
                print(f"Active default (resolve_gemini_api_key): {_mask(key)} from {label}")
                probe = _probe(key)
                print(f"  probe: {'OK' if probe.get('ok') else probe.get('error')}")
                break
    else:
        print("resolve_gemini_api_key(): no key resolved")

    return 0 if any_ok else 2


if __name__ == "__main__":
    sys.exit(main())
