"""Generate docs/BENCHMARK_RESULTS.md from H9 aggregate analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def _fmt_ci(d: Dict[str, Any] | None) -> str:
    if not d:
        return "—"
    return f"{d.get('point', 0):.4f} [{d.get('lower95', 0):.4f}, {d.get('upper95', 0):.4f}]"


def generate_results_md(aggregate_path: Path, out_path: Path) -> str:
    data = json.loads(aggregate_path.read_text(encoding="utf-8"))
    meta = data.get("meta") or {}
    bands = data.get("bands") or {}
    cal = data.get("belief_calibration_pooled") or {}

    lines = [
        "# ChorusGraph A/B Benchmark Results (H9)",
        "",
        "**Methodology:** [`BENCHMARK.md`](BENCHMARK.md) · **Fairness:** [`benchmark/FAIRNESS_H9.md`](../benchmark/FAIRNESS_H9.md)",
        "",
        f"- **Run at:** {meta.get('run_at', 'unknown')}",
        f"- **Environment:** {meta.get('environment', 'local')} *(Azure rerun required — see Quota)*",
        f"- **Tasks per band (target):** {meta.get('n_tasks_per_band', 1000)}",
        f"- **Repeat bands:** 20%, 40%, 60%",
        "",
        "> **No overall winner declared.** All metrics include 95% confidence intervals where valid.",
        "",
        "## Quota / run status",
        "",
        "Gemini daily quota (`gemini-2.5-flash`, 10k req/day) was exhausted mid-run:",
        "- **Band 20%:** ~599 valid paired tasks (of 1000) — results below use **valid rows only**.",
        "- **Bands 40% / 60%:** 100% quota-blocked (429) — **re-run on Azure with fresh API key/billing**.",
        "",
        "## Fairness confirmation (pre-run)",
        "",
        "- Container B uses **LLM ReAct/AgentNode** path (not regex researcher).",
        "- Accuracy rubric scores **answer content** identically for A and B.",
        "",
        "## Results with confidence intervals",
        "",
        data.get("ci_table_markdown", ""),
        "",
        "## Per-band detail",
        "",
    ]

    for band, band_data in sorted(bands.items(), key=lambda x: int(x[0])):
        if band_data.get("quota_blocked"):
            lines.extend([
                f"### Repeat band {band}% — **QUOTA BLOCKED**",
                "",
                f"- Valid tasks: 0 / {band_data.get('n_tasks')}",
                f"- Re-run required on Azure.",
                "",
            ])
            continue
        ab = band_data.get("compare_ab") or {}
        fp = ab.get("b_cache_fp_by_slug") or {}
        fx = fp.get("fx_rates") or {}
        lines.extend([
            f"### Repeat band {band}%",
            "",
            f"- Valid paired tasks: {ab.get('n_paired')} (excludes 429 quota errors)",
            f"- Workload stats: `{band_data.get('workload_stats')}`",
            f"- B cache hit-rate (Wilson 95% CI): {_fmt_ci((ab.get('b_cache') or {}).get('cache_hit_rate'))}",
            f"- Paired cost delta (B−A): {_fmt_ci(ab.get('cost_delta_usd_per_task'))}",
            f"- Paired latency delta (B−A ms): {_fmt_ci(ab.get('latency_delta_ms'))}",
            f"- fx_rates slug: n_serve={fx.get('n_would_serve')}, FP upper95={fx.get('fp_upper95')}, verdict={fx.get('verdict')}",
            "",
        ])

    lines.extend([
        "## Belief-knob calibration (derived, not enabled in production)",
        "",
        f"- `confidence_stop`: {cal.get('confidence_stop')}",
        f"- `groundedness_floor`: {cal.get('groundedness_floor')}",
        f"- `memory_confidence_gate`: {cal.get('memory_confidence_gate')}",
        f"- Notes: {cal.get('notes')}",
        "",
        "## Honest wins and losses (band 20% — valid tasks only)",
        "",
        "**Latency:** B is slower — paired delta +1963 ms [+1783, +2150] (B−A, 95% bootstrap CI).",
        "**Cost:** B is more expensive — paired delta +$0.00010/task [+$0.00009, +$0.00011].",
        "**Accuracy:** Tied within CI — A 54.6% [51.5%, 57.7%] vs B 54.1% [51.0%, 57.2%].",
        "**Cache:** No semantic cache hits at 20% repeat (hit-rate 0% [0%, 0.4%]); fx_rates slug INSUFFICIENT DATA (n_serve=0).",
        "",
        "**Surprising ChorusGraph disadvantage:** With fair LLM ReAct on both sides, B uses ~2.5 LLM calls/task vs A ~1.4,",
        "and is ~2× slower at P50 — graph depth (cache_gate + react + writer + validator) without cache benefit.",
        "",
        "Bands 40%/60% sensitivity **not yet measured** (quota). Hypothesis: cache benefit may appear at higher repeat rates.",
        "",
    ])

    text = "\n".join(lines)
    out_path.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    import sys

    agg = Path(sys.argv[1] if len(sys.argv) > 1 else "benchmark/results/h9_full/aggregate_analysis.json")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "docs/BENCHMARK_RESULTS.md")
    generate_results_md(agg, out)
    print(f"Wrote {out}")
