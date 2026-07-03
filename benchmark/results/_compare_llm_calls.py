"""Compare Gemini LLM call counts: HL2 vs D."""
import json
import sys
from pathlib import Path

RESULT_DIR = Path(__file__).parent / (sys.argv[1] if len(sys.argv) > 1 else "h14_healthcare_cd_postfix")


def load(name: str):
    p = RESULT_DIR / name
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def summarize(label: str, rows: list) -> None:
    if not rows:
        print(f"{label}: no data")
        return
    print(f"=== {label} (n={len(rows)}) ===")
    print(f"  Total Gemini calls: {sum(r['llm_calls'] for r in rows)}")
    print(f"  Avg calls/case:     {sum(r['llm_calls'] for r in rows) / len(rows):.2f}")
    print(f"  Avg latency:        {sum(r['latency_ms'] for r in rows) / len(rows):.0f} ms")
    print(f"  Avg tokens_in:      {sum(r['tokens_in'] for r in rows) / len(rows):.0f}")
    by_depth: dict = {}
    for r in rows:
        d = r["pipeline_depth"]
        by_depth.setdefault(d, []).append(r)
    for depth in sorted(by_depth):
        sub = by_depth[depth]
        print(
            f"  depth {depth}: n={len(sub)} "
            f"avg_llm={sum(x['llm_calls'] for x in sub) / len(sub):.1f} "
            f"avg_ms={sum(x['latency_ms'] for x in sub) / len(sub):.0f}"
        )
    print()


def main() -> None:
    c = load("container_c.jsonl")
    d = load("container_d.jsonl")

    summarize("HL2 (all cases)", c)
    summarize("HC2 (all cases)", d)

    d_miss = [r for r in d if not r.get("cache_hit")]
    d_hit = [r for r in d if r.get("cache_hit")]
    summarize("HC2 — CACHE MISS only", d_miss)
    summarize("HC2 — CACHE HIT only", d_hit)

    print("=== Same case: C vs D llm_calls ===")
    c_by = {r["case_id"]: r for r in c}
    for r in sorted(d, key=lambda x: x["case_id"]):
        cr = c_by.get(r["case_id"])
        if not cr:
            continue
        tag = "HIT" if r.get("cache_hit") else "MISS"
        delta = r["llm_calls"] - cr["llm_calls"]
        print(
            f"  {r['case_id']}  C={cr['llm_calls']}  D={r['llm_calls']} ({delta:+d})  "
            f"D-{tag}  latency C={cr['latency_ms']} D={r['latency_ms']}"
        )

    print()
    print("=== MAIN ISSUE CHECK: D miss vs C (should D use FEWER LLMs?) ===")
    for r in sorted(d_miss, key=lambda x: x["case_id"]):
        cr = c_by.get(r["case_id"])
        if not cr:
            continue
        print(
            f"  {r['case_id']} depth={r['pipeline_depth']}: "
            f"C hops={[h['hop'] for h in cr['hop_metrics'] if h['llm_calls']]} "
            f"D hops={[h['hop'] for h in r['hop_metrics'] if h['llm_calls']]}"
        )


if __name__ == "__main__":
    main()
