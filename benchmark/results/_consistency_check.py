"""Verify consistency: HL2 vs D across all 18 cases."""
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).parent / "h14_healthcare_cd_postfix"


def load(name):
    return [json.loads(l) for l in (ROOT / name).read_text().splitlines() if l.strip()]


def llm_hops(r):
    return [h["hop"] for h in r["hop_metrics"] if h["llm_calls"] > 0]


def hop_pattern(r):
    return " -> ".join(h["hop"] for h in r["hop_metrics"])


def stats(vals):
    if len(vals) < 2:
        return {"min": vals[0], "max": vals[0], "stdev": 0}
    return {
        "min": min(vals),
        "max": max(vals),
        "stdev": round(statistics.stdev(vals), 2),
        "range": max(vals) - min(vals),
    }


c = load("container_c.jsonl")
d = load("container_d.jsonl")

print("=" * 70)
print("CONTAINER C — consistency by depth")
print("=" * 70)
for depth in (2, 4, 6):
    sub = [r for r in c if r["pipeline_depth"] == depth]
    llms = [r["llm_calls"] for r in sub]
    lats = [r["latency_ms"] for r in sub]
    patterns = {hop_pattern(r) for r in sub}
    llm_hop_sets = {tuple(llm_hops(r)) for r in sub}
    print(f"\ndepth {depth} (n={len(sub)}):")
    print(f"  llm_calls:  {llms}  unique={set(llms)}  stats={stats(llms)}")
    print(f"  latency_ms: min={min(lats)} max={max(lats)} stdev={statistics.stdev(lats):.0f}")
    print(f"  hop patterns ({len(patterns)} unique): {patterns}")
    print(f"  LLM hop sequences ({len(llm_hop_sets)} unique):")
    for s in sorted(llm_hop_sets):
        print(f"    {list(s)}")

print("\n" + "=" * 70)
print("CONTAINER D — consistency by depth")
print("=" * 70)
for depth in (2, 4, 6):
    sub = [r for r in d if r["pipeline_depth"] == depth]
    llms = [r["llm_calls"] for r in sub]
    lats = [r["latency_ms"] for r in sub]
    hits = [r.get("cache_hit") for r in sub]
    patterns = {hop_pattern(r) for r in sub}
    llm_hop_sets = {tuple(llm_hops(r)) for r in sub}
    print(f"\ndepth {depth} (n={len(sub)}) cache_hits={sum(1 for h in hits if h)}/{len(sub)}:")
    print(f"  llm_calls:  {llms}  unique={set(llms)}  stats={stats(llms)}")
    print(f"  latency_ms: min={min(lats)} max={max(lats)} stdev={statistics.stdev(lats):.0f}")
    print(f"  hop patterns ({len(patterns)} unique):")
    for p in sorted(patterns):
        print(f"    {p}")
    print(f"  LLM hop sequences ({len(llm_hop_sets)} unique):")
    for s in sorted(llm_hop_sets):
        print(f"    {list(s)}")

print("\n" + "=" * 70)
print("CASE-BY-CASE: why C looks stable vs D")
print("=" * 70)
c_by = {r["case_id"]: r for r in c}
for dr in sorted(d, key=lambda x: x["case_id"]):
    cr = c_by[dr["case_id"]]
    print(f"\n{dr['case_id']} depth={dr['pipeline_depth']} variant={dr.get('variant')}")
    print(f"  C: {cr['llm_calls']} llm  {cr['latency_ms']}ms  hops={hop_pattern(cr)}")
    print(f"  D: {dr['llm_calls']} llm  {dr['latency_ms']}ms  hit={dr.get('cache_hit')}  hops={hop_pattern(dr)}")
    if cr["llm_calls"] != dr["llm_calls"]:
        print(f"  DELTA llm: D has {dr['llm_calls'] - cr['llm_calls']:+d}  "
              f"C_llm_hops={llm_hops(cr)}  D_llm_hops={llm_hops(dr)}")

print("\n" + "=" * 70)
print("ROOT CAUSE SUMMARY")
print("=" * 70)
# C writer llm at depth 6
c6 = [r for r in c if r["pipeline_depth"] == 6]
writer_llm_c6 = [next(h for h in r["hop_metrics"] if h["hop"] == "writer")["llm_calls"] for r in c6]
abstain_c6 = [r.get("abstained") for r in c6]
print(f"C depth-6 writer LLM calls per case: {writer_llm_c6}  abstained={abstain_c6}")

d6 = [r for r in d if r["pipeline_depth"] == 6]
for r in d6:
    wh = next(h for h in r["hop_metrics"] if h["hop"] == "writer")
    print(f"  D {r['case_id']} hit={r.get('cache_hit')} writer_llm={wh['llm_calls']} abstained={r.get('abstained')}")
