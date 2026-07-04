# Handoff return — Bug-1 (HC2 depth-6 cache-hit routing)

**Date:** 2026-07-04

## 1. Logged evidence (step 3)

### Pre-fix (`light_20260704`) — consumption bug, not core

Committed `first_judgment_hop_after_cache` had **`return "safety"` before any analyze check at depth ≥ 6**. All 10/10 depth-6 cache hits: `cache_gate → safety → writer` in `hop_metrics`.

Handoff §2 claim that isolated calls return `"analyze"` was **incorrect** for committed code.

### Post-routing-fix (`hc2fix_20260704`) — core exonerated

```json
{"event": "route_after_cache", "case_id": "case-002-d6-05", "route": "analyze", "hop_artifact_keys": ["intake"]}
{"event": "core_route_ledger", "steps": [
  {"node": "cache_gate", "edge_taken": "analyze"},
  {"node": "analyze", "edge_taken": "drug_check"},
  {"node": "drug_check", "edge_taken": "safety"}
]}
```

**Hypothesis confirmed:** consumption routing order in `benchmark/hc2/cache_helpers.py` — **not** scheduler snapshot timing, channel reducers, or stale `NodeContext`.

## 2. Fixes applied (this pass)

| Track | Change | Files |
|-------|--------|-------|
| Routing | d6 cache hit → `analyze` when analyze missing/empty; then linear graph runs drug_check → safety | `cache_helpers.py` |
| Track B | `analyze_handoff_plain` / `safety_handoff_plain` use `state.retrieved` when hop retrieve absent | `artifacts.py`, `nodes.py` |
| Track B | `cache_query_key(case)` gate + **`cache_payload_sufficient`** rejects intake-only hits at depth ≥ 4 | `runner.py`, `cache_helpers.py` |
| Track B | Seed depth-suffixed keys only (no plain paraphrase pollution) | `cache_helpers.py` |
| Track A | D-writer prompts + `writer_must_cite_block(must_cite)` | `prompts.py`, `nodes.py` |
| Logs | `hop_artifact_keys`, `agents` on `route_after_cache`; fix `has_analyze` via `hop_artifact_has_content` | `nodes.py` |
| Docs | `PARITY.md`, wiring tests | `PARITY.md`, `wiring.py`, `tests/` |

**Explicitly NOT done:** stuffing cache with more seeds to inflate benchmark scores.

## 3. Exit criteria (§4) — v2 repeat runs

Command (×3 seeds):

```bash
python -m benchmark.run_scenarios --scenarios HL2,HC2 --tier light --temperature 0.0 --seed {42,43,44}
```

Output dirs: `benchmark/results/mvp_scenarios/hc2fix_v2_seed{42,43,44}/`

### Overall (40 tasks each)

| Seed | HL2 success | HC2 success | HC2 cache hit |
|------|-------------|-------------|---------------|
| 42 | 70.0% (28/40) | 85.0% (34/40) | 30.0% (12/40) |
| 43 | 57.5% (23/40) | 92.5% (37/40) | 20.0% (8/40) |
| 44 | 50.0% (20/40) | 77.5% (31/40) | 25.0% (10/40) |

Pre-fix no-cache baseline (`honest_hl2_hc2_20260703`): HL2 **62.5%**, HC2 **55%**.

**Track A (citations)** clearly moved cold-path success — HC2 77–92% vs 55% baseline. HL2 swings 50–70% (seed/workload noise on small n).

**Track B (cache)** is working again after reverting depth-only gate keys (repeat runs with depth-only gate had **0%** hits). Hit rate 20–30% vs pre-fix **62.5%** — expected: `cache_payload_sufficient` rejects intake-only seeds; routing no longer writer-only on d6 hits.

### Depth-6 cache-hit subgroup (n≈13 d6 cases, 3–8 hits per run)

| Seed | d6 cache hits | d6 hit success |
|------|---------------|----------------|
| 42 | 5 | **4/5** (1 cite miss: ASCVD on `case-008-d6-35`) |
| 43 | 3 | **3/3** |
| 44 | 8 | **4/8** |

Routing fix verified on seed-42 trace: d6 hits route `cache_gate → analyze → drug_check → safety → writer` (not `safety`-first).

**Interpretation (methodology):** hit-count swings **3–8** and success-on-hits **3/3–4/8** across three seeds — consistent with compounding noise floor at n≈10. A single-run delta (e.g. 4/10→3/10) is **not** distinguishable from noise. Need more d6 cases in workload or many more repeats for a trustworthy routing-only read.

**What we can say:** fixes are landed and behaving as designed; overall HC2 success up sharply (mostly citations); d6 cache path runs analyze again; insufficient-payload hits downgrade to cold path.

## 4. HL2 variant label (§5)

Not fixed in this pass.

## 5. Open

- Depth-6 cache-hit success: **3–4 successes per run on 3–8 hits** — noise floor confirmed; expand d6 workload before claiming routing delta.
- Citation misses on cache-hit path still possible (`missing_cite_terms` in trace); Track A helps cold path more than cache-hit writer.
- Overall cache hit rate lower than pre-fix 62.5% — trade-off for payload sufficiency + no benchmark gaming.
