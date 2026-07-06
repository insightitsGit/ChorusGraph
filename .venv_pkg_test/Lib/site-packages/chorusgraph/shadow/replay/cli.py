"""CLI for production shadow replay."""

from __future__ import annotations

import argparse
from pathlib import Path

from chorusgraph.shadow.replay.replay import run_temporal_replay
from chorusgraph.shadow.replay.report import format_production_report, recommend_thresholds, build_slug_reports

DEFAULT_JSONL = Path(__file__).resolve().parent / "data" / "website_chat_turns.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Production shadow replay (temporal split)")
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--seed-fraction", type=float, default=0.70)
    parser.add_argument("--coarse", type=float, default=0.88)
    args = parser.parse_args()

    if not args.jsonl.exists():
        raise SystemExit(f"JSONL not found: {args.jsonl}")

    result = run_temporal_replay(
        args.jsonl,
        seed_fraction=args.seed_fraction,
        coarse_threshold=args.coarse,
    )
    print(
        format_production_report(
            result,
            source=str(args.jsonl),
        )
    )
    rec = recommend_thresholds(build_slug_reports(result))
    if rec:
        print("\nRecommended verify thresholds (CACHEABLE only):")
        for slug, thresh in sorted(rec.items()):
            print(f"  {slug}: {thresh:.2f}")


if __name__ == "__main__":
    main()
