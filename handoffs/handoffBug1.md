# Handoff Bug-1 — HC2 depth-6 cache-hit path silently skips analyze + drug_check

**Director:** Amin · **Architect:** Claude · **Engineer:** Cursor
**Source run:** `benchmark/results/mvp_scenarios/light_20260704/hc2.jsonl` (temp=0.0, deterministic — see §0)
**Date issued:** 2026-07-04

---

## 0. Why this run is trustworthy (read once)

A prior investigation found Gemini calls ran at `temperature=0.2`, which made two runs of byte-identical
code disagree on 36/40 answers — noise large enough to hide or fake any real signal. `benchmark_flags.py`
now exposes `--temperature` (default 0.2 unchanged; `run_scenarios.py --temperature 0.0` for controlled
comparisons), and this run used it. **Verified:** with real repeat pairs matched by session (not by raw
text — a naive text-match check gave a false 7/11 the first time), FL1 reproduces **11/11 identical**
answers at temp=0.0. The instrument is clean. Everything below is diagnosed on data you can trust.

---

## 1. The bug, precisely

**Symptom:** HC2 (ChorusGraph healthcare multi-agent) trails HL2 (LangGraph baseline) on success —
45% vs 60% in the `light_20260704` run — concentrated entirely at **pipeline depth 6, on cache hits**:
depth-6 cache-hit success is 4/10 (40%), vs depth-6 cold-path success 2/3 (67%).

**Root cause, verified from the actual per-row `hop_metrics` (ground truth, not inferred):**

| Path | Actual hop sequence (from `hop_metrics`) |
|---|---|
| Depth-6 **cold** (`case-004-d6-02`, `case-012-d6-08`) | `vector_ingress → cache_gate → intake → retrieve → analyze → drug_check → safety → writer` |
| Depth-6 **cache-hit** (ALL 10 of 10 rows, incl. the 4 that succeeded) | `vector_ingress → cache_gate → safety → writer` |

**On every single depth-6 cache hit, `analyze` and `drug_check` are skipped entirely — not just for
failing cases, for all 10.** `safety_node` (`benchmark/hc2/nodes.py:257`) is the only place `abstained`
gets computed (`should_abstain(...)` at line 275), and it is making that judgment with **zero analysis
reasoning artifact** — only the cached facts (`retrieve`, `drug_check` payload) reach it, because
`facts_only_payload` (`benchmark/shared/healthcare_cache.py:17`) deliberately excludes `analyze` from
what gets cached/restored (archetype-C design intent: judgment hops must stay fresh). The intent was
for `analyze` to be re-run fresh on a cache hit at depth ≥ 6 — that's what
`first_judgment_hop_after_cache` (`benchmark/hc2/cache_helpers.py:163`) is supposed to guarantee — but
in the live run it never activates.

**Consequence:** `safety` under-informed defaults to caution far more often than the cold path does —
6 of 10 depth-6 hits abstain (`"ABSTAIN: insufficient grounded evidence..."`, the hardcoded string at
`nodes.py:293`), and 5 of those 6 are scored FAIL. **This is the entire HC2 gap.** The prior handoff's
depth-aware fingerprint fix (`PrismRagAddition` Part A) could never have closed this — it only changes
*which* entries match, not that every depth-6 hit loses the analyze step regardless of which entry it
matched.

---

## 2. What I already verified — do NOT re-investigate these

- ✅ `first_judgment_hop_after_cache` **is correct in isolation.** Called directly with a hand-built
  state simulating a clean post-cache-restore (`hop_artifacts` = only `intake`/`retrieve`/`drug_check`,
  `pipeline_depth=6`), it correctly returns `"analyze"`. **The function's own logic is not the bug.**
- ✅ `agents` passed to the router **is confirmed correct**: `build_healthcare_graph_hc2` sets
  `agents = PIPELINE_AGENTS[depth]`, and `PIPELINE_AGENTS[6]` (`benchmark/healthcare_workload.py:136`)
  literally includes `"analyze"`. Not a missing-agent-in-list bug.
- ✅ **Not a checkpoint/thread_id resume bug.** `HC2Runner.run()` (`benchmark/hc2/runner.py:187`) calls
  `compiled.invoke({...})` with **no `config`/`thread_id` kwarg at all**, and the input dict explicitly
  sets `"hop_artifacts": {}` fresh on every call. No checkpointer is attached to this graph. The
  scheduler's `_init_run` only resumes when `input is None` — never true here. Ruled out with evidence,
  not assumption.
- ✅ `facts_only_payload` (`benchmark/shared/healthcare_cache.py:17`) correctly filters `hop_artifacts`
  to only `intake`/`retrieve`/`drug_check` — `analyze` is never part of what a cache hit restores.
  `apply_cache_payload` (`benchmark/hc2/cache_helpers.py:185`) does not set `abstained` — confirmed
  current code, this file was recently rewritten and no longer replays a stale `abstained` flag.

**So the leak is real, reproducible (10/10), but its exact mechanism is not yet located** — it happens
somewhere between cache_gate's own update and the router's read of `state`/`hop_artifacts`, WITHIN a
single `invoke()` call (ruled out: across-call/session leakage). This is the one open question.

---

## 3. Required first step: instrument before you patch

Do not guess a fix. Add one diagnostic (a `trace_event` call, or a temporary `print`) immediately before
the routing decision in `route_after_cache_hc2` (`benchmark/hc2/nodes.py:84`) and inside
`first_judgment_hop_after_cache` (`benchmark/hc2/cache_helpers.py:163`) for a live run, logging at
minimum:
- `sorted(state.get("hop_artifacts", {}).keys())` — is `"analyze"` really present/truthy here, or is
  something else causing the branch skip?
- `agents` as actually received by the closure at call time (confirm it's really `PIPELINE_AGENTS[6]`
  and not some other list mutated elsewhere).
- `state.get("cache_hit")`, `state.get("cache_facts")` — confirm the branch condition
  (`if state.get("cache_hit") and state.get("cache_facts"):`) is true for the right reason.

Reproduce with:
```powershell
python -m benchmark.run_scenarios --scenarios HL2,HC2 --tier light --temperature 0.0
```
(matches the Director's own in-flight diagnostic run — a full log with only HL2/HC2 enabled, to isolate
whether the defect is in `chorusgraph/core` (engine: reducers, `NodeContext.read()`, scheduler snapshot
timing) or in the consumption code (`benchmark/hc2/*`: the router, the cache-hit merge, or graph wiring).
**Bring the actual logged values into the handoff-back — do not reason from code alone, as I already
disproved one plausible-sounding theory (checkpoint resume) that would have wasted a fix cycle.**

**Ranked hypotheses to check, in order (cheapest to verify first):**
1. The scheduler's conditional-edge router (`GraphIR.successors`, `chorusgraph/core/ir.py`) may evaluate
   the routing function against a **different state snapshot** than the one `cache_gate`'s own update
   just produced (a super-step read-before-write timing issue) — check whether `view` passed to the
   router reflects the merged `hop_artifacts` from `cache_gate`'s own returned update, or a snapshot
   from before it.
2. A channel reducer for `hop_artifacts` may not be a plain dict-replace and could be re-merging keys
   from an unexpected source (check `chorusgraph/core/channels.py` reducer for whatever key
   `hop_artifacts` uses — is it `operator.add`-style, dict-merge, or replace?).
3. `NodeContext.read()` (or whatever `_read_view` in `nodes.py` calls) might return a cached/stale
   view object rather than the live merged state at the exact point the conditional edge evaluates.

---

## 4. Fix (only after step 3 confirms the mechanism)

Whatever the located cause, the fix must restore this invariant: **a depth-6 facts-cache-hit re-runs
`analyze` fresh before `safety`, exactly as `first_judgment_hop_after_cache`'s own logic (already
correct in isolation) intends.** Do not special-case around the symptom (e.g., don't just force-route to
"analyze" unconditionally) without knowing why the existing correct-in-isolation check fails live —
that risks masking a deeper engine-level state-timing bug that could affect other node×cache
interactions beyond HC2.

**Exit criteria:**
- Re-run `python -m benchmark.run_scenarios --scenarios HL2,HC2 --tier light --temperature 0.0`.
- Every depth-6 cache-hit row's `hop_metrics` must include `analyze` (and `drug_check` if the cold path
  includes it) before `safety`.
- Report the new depth-6 cache-hit success rate — expect it to approach the cold-path rate (2/3 ≈ 67%),
  not necessarily hit it exactly (n is small; state the raw count, not just the percentage).
- Full `python -m pytest tests/ -q` green.

---

## 5. Secondary, lower-priority: HL2 variant-label bug (cosmetic, not blocking)

`benchmark/hl2/runner.py`'s measurement row construction never records the real `variant`
(`novel`/`exact_repeat`/`paraphrase`) — confirmed across all three recent runs, HL2 always reports
`Counter({'novel': 40})` even though the shared workload (`generate_healthcare_workload`, same call used
by HC1/HC2 which DO show the correct mix) contains real repeats. **Does not affect `task_success`/
latency scoring** — it's a measurement-row labeling gap only. Fix whenever convenient; not required
before re-measuring Bug-1's fix, and not related to it (traced to a different file, different mechanism).

---

## Return format (`handoffbackBug1.md`)

1. The actual logged values from step 3 (real state, not inferred) for at least 2 depth-6 cache-hit
   cases — this is the evidence the fix decision rests on.
2. Which of the 3 ranked hypotheses (or a 4th, if found) was confirmed, with the log lines that prove it.
3. The fix applied, files changed.
4. Exit criteria from §4 — pass/fail with real command output, the new depth-6 cache-hit success count.
5. Whether §5 (HL2 variant label) was also fixed in the same pass — optional, state either way.
6. Anything you could not pin down — stated plainly, not papered over.

No commits unless the Director asks.

---
*Bug-1 · precise, reproduced (10/10), one theory already disproven with evidence, one open question
requiring live instrumentation before any patch is written.*
