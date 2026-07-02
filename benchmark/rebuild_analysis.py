"""Rebuild analysis JSON from existing JSONL without re-running tasks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from benchmark.analyze import compare_ab, format_ci_table, valid_rows
from benchmark.belief_calibration import calibrate_from_measurements
from benchmark.jsonl_io import load_measurements
from benchmark.thresholds import measured_thresholds
from benchmark.workload import generate_workload, workload_stats


def rebuild(out_dir: Path, bands: list[int], n_tasks: int = 1000, seed: int = 42) -> dict:
    band_results = {}
    all_b = []
    for band in bands:
        path_a = out_dir / f"band_{band}_container_a.jsonl"
        path_b = out_dir / f"band_{band}_container_b.jsonl"
        a_rows = load_measurements(path_a)
        b_rows = load_measurements(path_b)
        tasks = generate_workload(n_tasks, seed=seed + band, repeat_band_pct=band)
        n_valid_a = len(valid_rows(a_rows))
        n_valid_b = len(valid_rows(b_rows))
        n_quota = sum(1 for r in a_rows + b_rows if r.error and "429" in (r.error or ""))
        comparison = compare_ab(a_rows, b_rows)
        calibration = calibrate_from_measurements(valid_rows(b_rows))
        band_results[band] = {
            "repeat_band_pct": band,
            "n_tasks": len(a_rows),
            "n_valid_a": n_valid_a,
            "n_valid_b": n_valid_b,
            "n_quota_blocked": n_quota,
            "quota_blocked": n_valid_a < n_tasks * 0.5,
            "seed": seed + band,
            "workload_stats": workload_stats(tasks),
            "compare_ab": comparison,
            "belief_calibration": calibration.to_dict(),
            "thresholds": {
                "coarse": measured_thresholds().coarse,
                "verify_fx_rates": measured_thresholds().verify_for("fx_rates"),
            },
        }
        (out_dir / f"band_{band}_analysis.json").write_text(
            json.dumps(band_results[band], indent=2), encoding="utf-8"
        )
        all_b.extend(valid_rows(b_rows))

    aggregate = {
        "meta": json.loads((out_dir / "run_meta.json").read_text(encoding="utf-8"))
        if (out_dir / "run_meta.json").exists()
        else {},
        "bands": band_results,
        "belief_calibration_pooled": calibrate_from_measurements(all_b).to_dict(),
        "ci_table_markdown": format_ci_table({
            b: {"compare_ab": band_results[b]["compare_ab"]}
            for b in bands
            if not band_results[b].get("quota_blocked")
        }),
    }
    (out_dir / "aggregate_analysis.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    return aggregate


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "benchmark/results/h9_full")
    bands = [int(b.strip()) for b in (sys.argv[2] if len(sys.argv) > 2 else "20,40,60").split(",")]
    agg = rebuild(out, bands)
    print(f"Rebuilt aggregate for bands {bands} -> {out / 'aggregate_analysis.json'}")
