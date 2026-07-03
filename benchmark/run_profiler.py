"""CLI — run CacheProfile profiler on recorded fixtures (H21 T6)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from benchmark.profiler import run_profiler


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure CacheProfile attributes from fixtures")
    parser.add_argument(
        "--categories",
        nargs="+",
        default=["fx_rates", "clinical_guidelines"],
        help="Category slugs with fixtures in benchmark/fixtures/profiler/",
    )
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        help="Run id for output directory",
    )
    args = parser.parse_args()

    manifest = run_profiler(args.categories, run_id=args.run_id)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
