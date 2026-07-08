"""One-off: analyze FC2 vs FL2 failures from mid benchmark jsonl."""
import json
from collections import Counter
from pathlib import Path

base = Path(__file__).resolve().parents[1] / "benchmark/results/azure_mid_20260707_220458/mvp_scenarios/mid_20260707_220458/mid_20260707_220458"


def load(name: str):
    rows = []
    for line in (base / name).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main():
    fl2 = load("fl2.jsonl")
    fc2 = load("fc2.jsonl")
    fl2_by = {r["task_id"]: r for r in fl2}
    fc2_by = {r["task_id"]: r for r in fc2}

    print("=== Raw success rates ===")
    print(f"FL2: {sum(r['task_success'] for r in fl2)}/{len(fl2)}")
    print(f"FC2: {sum(r['task_success'] for r in fc2)}/{len(fc2)}")

    print("\n=== FL2 errors (excluded from report valid set) ===")
    err_rows = [r for r in fl2 if r.get("error")]
    print(f"count: {len(err_rows)}")
    for e, n in Counter((r.get("error") or "")[:100] for r in err_rows).most_common(5):
        print(f"  {n}x {e}")

    # simulate compare_scenarios valid filter
    def valid(r):
        if r.get("error"):
            return False
        return r.get("llm_calls", 0) > 0 or r.get("cache_hit") or len(str(r.get("task_id", ""))) > 0

    fl2_valid = [r for r in fl2 if valid(r)]
    fc2_valid = [r for r in fc2 if valid(r)]
    print("\n=== After compare_scenarios valid filter ===")
    print(
        f"FL2 valid: {len(fl2_valid)} success {sum(r['task_success'] for r in fl2_valid)}/{len(fl2_valid)}"
        f" = {sum(r['task_success'] for r in fl2_valid)/len(fl2_valid):.1%}"
    )
    print(
        f"FC2 valid: {len(fc2_valid)} success {sum(r['task_success'] for r in fc2_valid)}/{len(fc2_valid)}"
        f" = {sum(r['task_success'] for r in fc2_valid)/len(fc2_valid):.1%}"
    )

    print("\n=== FC2 failure categories ===")
    cats = Counter()
    for r in fc2:
        if r["task_success"]:
            continue
        ans = r.get("answer") or ""
        if "annual_rate" in ans and "Disallowed" in ans:
            cats["compound_wrong_arg_name"] += 1
        elif any(x in ans.lower() for x in ("cannot answer", "don't have", "no record", "not contain")):
            cats["memory_recall_miss"] += 1
        elif r.get("error"):
            cats["exception"] += 1
        else:
            cats["rubric_other"] += 1
    for k, v in cats.most_common():
        print(f"  {k}: {v}")

    print("\n=== Paired head-to-head (all 100 tasks) ===")
    common = sorted(set(fl2_by) & set(fc2_by))
    l_ok_c_fail = sum(1 for i in common if fl2_by[i]["task_success"] and not fc2_by[i]["task_success"])
    c_ok_l_fail = sum(1 for i in common if fc2_by[i]["task_success"] and not fl2_by[i]["task_success"])
    print(f"L wins only: {l_ok_c_fail}, C wins only: {c_ok_l_fail}")


if __name__ == "__main__":
    main()
