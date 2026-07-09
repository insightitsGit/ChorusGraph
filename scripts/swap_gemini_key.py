"""Swap ChorusGraph GEMINI_API_KEY to meeting-scheduler backup key."""

from __future__ import annotations

from pathlib import Path


def read_key(path: Path, name: str = "GEMINI_API_KEY") -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key.strip() == name:
            return val.strip().strip('"').strip("'")
    return None


def mask(key: str) -> str:
    return f"...{key[-4:]}" if len(key) >= 4 else "***"


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    env_path = repo / ".env"
    ms_path = Path(r"c:\code\InsightitsAIAgent\meeting-scheduler\db_connection.local.env")

    old = read_key(env_path)
    alt = read_key(ms_path)
    if not old:
        print("No GEMINI_API_KEY in ChorusGraph/.env")
        return 1
    if not alt:
        print("No GEMINI_API_KEY in meeting-scheduler env")
        return 1
    if old == alt:
        print(f"Already using {mask(alt)}")
        return 0

    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    out: list[str] = []
    replaced = False
    bench_saved = False
    for line in lines:
        s = line.strip()
        if s.startswith("GEMINI_API_KEY_BENCHMARK="):
            out.append(f"GEMINI_API_KEY_BENCHMARK={old}")
            bench_saved = True
            continue
        if s.startswith("GEMINI_API_KEY=") and not s.startswith("GEMINI_API_KEY_"):
            out.append(f"GEMINI_API_KEY={alt}")
            replaced = True
            continue
        out.append(line)
    if not bench_saved:
        out.append(f"GEMINI_API_KEY_BENCHMARK={old}")
    if not replaced:
        out.append(f"GEMINI_API_KEY={alt}")

    env_path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"Switched GEMINI_API_KEY: {mask(old)} -> {mask(alt)}")
    print(f"Saved old key as GEMINI_API_KEY_BENCHMARK={mask(old)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
