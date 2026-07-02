"""Generate docs/BENCHMARK_RESULTS.md from volume aggregate analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def _fmt_ci(d: Dict[str, Any] | None) -> str:
    if not d:
        return "—"
    return f"{d.get('point', 0):.4f} [{d.get('lower95', 0):.4f}, {d.get('upper95', 0):.4f}]"


def _delta_sentence(label: str, delta: Dict[str, Any] | None, *, unit: str = "") -> str:
    if not delta:
        return f"- **{label}:** insufficient paired data"
    point = float(delta.get("point", 0))
    lo = float(delta.get("lower95", 0))
    hi = float(delta.get("upper95", 0))
    direction = "B higher" if point > 0 else "B lower" if point < 0 else "tied"
    return (
        f"- **{label}:** {direction} — paired delta {point:+.4f}{unit} "
        f"[{lo:+.4f}, {hi:+.4f}] (B−A, 95% bootstrap CI)"
    )


def _band_summary(band: str, band_data: Dict[str, Any]) -> list[str]:
    if band_data.get("quota_blocked"):
        return [
            f"### Repeat band {band}% — **QUOTA BLOCKED**",
            "",
            f"- Valid tasks: {band_data.get('n_valid_b', 0)} / {band_data.get('n_tasks', 0)}",
            f"- Quota errors (429): {band_data.get('n_quota_blocked', 0)}",
            "",
        ]
    ab = band_data.get("compare_ab") or {}
    fp = ab.get("b_cache_fp_by_slug") or {}
    fx = fp.get("fx_rates") or {}
    a_acc = (ab.get("container_a") or {}).get("accuracy_rate") or {}
    b_acc = (ab.get("container_b") or {}).get("accuracy_rate") or {}
    cache = (ab.get("b_cache") or {}).get("cache_hit_rate") or {}
    lines = [
        f"### Repeat band {band}%",
        "",
        f"- Valid paired tasks: {ab.get('n_paired')} (excludes 429 quota errors)",
        f"- Workload stats: `{band_data.get('workload_stats')}`",
        f"- Task success A: {_fmt_ci(a_acc)}",
        f"- Task success B: {_fmt_ci(b_acc)}",
        f"- B cache hit-rate (Wilson 95% CI): {_fmt_ci(cache)}",
        _delta_sentence("Cost", ab.get("cost_delta_usd_per_task"), unit=" USD/task"),
        _delta_sentence("Latency", ab.get("latency_delta_ms"), unit=" ms"),
        f"- fx_rates slug: n_serve={fx.get('n_would_serve')}, FP upper95={fx.get('fp_upper95')}, verdict={fx.get('verdict')}",
        "",
    ]
    return lines


def generate_results_md(aggregate_path: Path, out_path: Path) -> str:
    data = json.loads(aggregate_path.read_text(encoding="utf-8"))
    meta = data.get("meta") or {}
    bands = data.get("bands") or {}
    cal = data.get("belief_calibration_pooled") or {}
    run_label = meta.get("run_label", "H10")

    lines = [
        f"# ChorusGraph A/B Benchmark Results ({run_label})",
        "",
        "**Methodology:** [`BENCHMARK.md`](BENCHMARK.md) · **Fairness:** [`benchmark/FAIRNESS_H9.md`](../benchmark/FAIRNESS_H9.md)",
        "",
        f"- **Run at:** {meta.get('run_at', 'unknown')}",
        f"- **Environment:** {meta.get('environment', 'local')}",
        f"- **Code:** post-fix v0.9.1 (compound routing + canonical rubric)",
        f"- **Tasks per band (target):** {meta.get('n_tasks_per_band', 1000)}",
        f"- **Repeat bands:** {', '.join(str(b) for b in meta.get('bands', []))}%",
        "",
        "> **No overall winner declared.** All metrics include 95% confidence intervals where valid.",
        "",
        "## Fairness (H10 §2.4)",
        "",
        "- Container B uses **LLM ReAct/AgentNode** for FX (not regex researcher).",
        "- **Canonical rubric** scores grounded FX pair + compound FV (`benchmark/rubric.py`).",
        "- B-only **template writer** and **compound fast path** disclosed in `FAIRNESS_H9.md` §3.",
        "",
        "## Results with confidence intervals",
        "",
        data.get("ci_table_markdown", ""),
        "",
        "## Per-band detail",
        "",
    ]

    for band, band_data in sorted(bands.items(), key=lambda x: int(x[0])):
        lines.extend(_band_summary(str(band), band_data))

    lines.extend([
        "## Belief-knob calibration (derived, not enabled in production)",
        "",
        f"- `confidence_stop`: {cal.get('confidence_stop')}",
        f"- `groundedness_floor`: {cal.get('groundedness_floor')}",
        f"- `memory_confidence_gate`: {cal.get('memory_confidence_gate')}",
        f"- Notes: {cal.get('notes')}",
        "",
        "## Cache thesis (H10 open question)",
        "",
        "Does semantic cache earn its overhead at 40%/60% repeat? See per-band **b_cache_hit_rate**",
        "and paired cost/latency deltas above. Band 20% (~80% novel) is not cache-exercising by design.",
        "",
    ])

    text = "\n".join(lines)
    out_path.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    import sys

    agg = Path(sys.argv[1] if len(sys.argv) > 1 else "benchmark/results/h10_volume/aggregate_analysis.json")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "docs/BENCHMARK_RESULTS.md")
    generate_results_md(agg, out)
    print(f"Wrote {out}")
