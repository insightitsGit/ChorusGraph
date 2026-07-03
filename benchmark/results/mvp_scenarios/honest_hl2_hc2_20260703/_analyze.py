"""Analyze honest HL2/HC2 run."""
import json
from collections import defaultdict
from pathlib import Path

base = Path("benchmark/results/mvp_scenarios/honest_hl2_hc2_20260703")


def load(name: str):
    return [json.loads(l) for l in (base / name).read_text(encoding="utf-8").splitlines() if l.strip()]


hl2, hc2 = load("hl2.jsonl"), load("hc2.jsonl")
print("Cache hits HL2:", sum(1 for r in hl2 if r.get("cache_hit")))
print("Cache hits HC2:", sum(1 for r in hc2 if r.get("cache_hit")))
print()
for label, rows in [("HL2", hl2), ("HC2", hc2)]:
    by_v: dict = defaultdict(list)
    for r in rows:
        by_v[r.get("variant", "novel")].append(r)
    print(label)
    for v in sorted(by_v):
        sub = by_v[v]
        n = len(sub)
        succ = sum(r["task_success"] for r in sub) / n
        llm = sum(r["llm_calls"] for r in sub) / n
        print(f"  {v}: n={n} success={succ:.1%} llm={llm:.2f}")

hl = {r["case_id"]: r for r in hl2}
hc = {r["case_id"]: r for r in hc2}
l_only = c_only = tie = 0
for cid in hl:
    ls, cs = hl[cid]["task_success"], hc[cid]["task_success"]
    if ls and not cs:
        l_only += 1
    elif cs and not ls:
        c_only += 1
    else:
        tie += 1
print(f"\nPaired: HL2-only wins {l_only}, HC2-only wins {c_only}, tie {tie}")
