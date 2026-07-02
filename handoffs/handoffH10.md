# Handoff H10 — MVP Finish: fixes + the real cache validation

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/BENCHMARK.md`](../docs/BENCHMARK.md), [`../docs/BENCHMARK_RESULTS.md`](../docs/BENCHMARK_RESULTS.md), handoffback9, DESIGN §7.6/§8/§13.
**Return in:** `handoffs/handoffbackH10.md`.

**This is the final MVP handoff.** H9 ran the benchmark but couldn't *finish* it — quota blocked 2 of 3
bands, the workload was 83% novel (so the cache never engaged), and two defects remain. H10 closes and
**validates** the MVP: fix the defects, then run the test that actually answers *"does the cache earn its
overhead?"* The enterprise track (E1–E9) is separate and comes after.

## 0. Operating rules
No fakes — real Gemini, real Azure run. Report honest wins **and** losses. **Freeze B's design** except the
two named defect fixes — no more "lost the benchmark → change B → rerun." Fix bugs transparently, then run clean.

## 1. Goal
Close the MVP with a **validated** result: the two defects fixed, and a clean, fair, at-volume benchmark on a
**cache-exercising** workload across all repeat bands — so we finally know whether the cache delivers.

## 2. Deliverables

### 2.1 Fix — compound-interest routing (real defect)
B's ReAct calls `fetch_exchange_rate` for compound-interest questions. Route compound tasks to the
`compound_interest` tool (taxonomy router → correct tool, or deterministic calculator). That task class must pass.

### 2.2 Fix — grounded-number rubric (honesty)
Today a task "passes" if the answer merely *contains* a decimal — even a hallucinated one, which lets A
"win" on ungrounded numbers. Change `score_task_success()`: a number counts **only if it traces to a tool
result** (grounded). Apply identically to A and B.

### 2.3 Cache-exercising workload (the missing test condition)
Band-20 was 83% novel → 0% cache by construction. Build a workload that actually tests the cache:
- Higher, realistic repeat/paraphrase rates (this is what the 20/40/60 bands are for).
- **Memory-bearing tasks** so Cortex recall fires (the belief signals were null in H9 for lack of these).
- Mixed FX + compound. Document the repeat model.

### 2.4 Fairness resolution (Director call)
The post-fix template writer is a B-only advantage A lacks. Resolve **one** way, and disclose it:
either give A the equivalent template/deterministic path, **or** document it as a ChorusGraph framework
feature and argue it honestly in `FAIRNESS_H9.md`. No silent asymmetry.

### 2.5 The real run — Azure, all bands, at volume, with CIs
Quota-solved (dedicated key/billing). Run bands **20/40/60** at ≥1000 tasks each, paired A∥B, per-task
JSONL + aggregate report, **confidence intervals** throughout. This is the run H9 couldn't complete.

### 2.6 Belief-knob calibration
From the measured grounding/confidence distributions (now non-null, thanks to the memory tasks), derive
`confidence_stop` / `groundedness_floor` thresholds (§7.5). Calibrate; enabling in production stays later.

### 2.7 Cortex recall generalization
Remove the demo-specific fallback query (the hardcoded "risk tolerance") from `recall_for_turn`; rely on
the general profile recall. So cross-session memory works on the benchmark's memory tasks, not just the demo.

### 2.8 Docs + release
- Vector-orchestrator boundary principle → DESIGN §6–§7 + WORKFLOW (internal hops = vectors/facts, template/ONNX, LLM only at the boundary).
- `BENCHMARK_RESULTS.md` updated with the clean all-band numbers + honest wins/losses.
- Tag the release (**v0.9.1** or **v0.10.0** — Director's call).

## 3. Out of scope (deferred, NOT MVP-blocking — listed so nothing is lost)
- H7 stubbed convenience knobs (`critic_model` wiring, `evaluator` backends, durable `checkpoint_after_step`, `on_exhaust`/`trace_level` behavior).
- Durable Cortex GraphStore + multi-DB (→ E5).
- The separate load/throughput test (→ E7).
- The entire enterprise track E1–E9.
- Enabling belief-knobs in production (calibrate only here).

## 4. Acceptance criteria
- [ ] Compound-interest routes to the correct tool; that task class passes.
- [ ] Rubric credits **grounded** numbers only; A's ungrounded "wins" no longer count.
- [ ] Cache-exercising workload runs all 3 bands (20/40/60) at volume, paired, with CIs, on Azure.
- [ ] **Cache hit-rate + cost/latency delta reported per band** — the actual answer to "does the cache deliver."
- [ ] Belief thresholds calibrated (or a documented reason they're still null).
- [ ] Fairness resolved and disclosed; `BENCHMARK_RESULTS.md` shows honest wins **and** losses with CIs.
- [ ] Tagged release; docs updated. No mocks. **No winner claim without CIs.**

## 5. Open questions for handoffbackH10
1. **Does the cache deliver at 40%/60% repeat?** Hit-rate + cost/latency saving per band.
2. Calibrated belief thresholds — what came out?
3. Net A/B result with CIs, once routing + rubric + fairness are clean — does B win, lose, or split, and where?
4. Any residual asymmetry a skeptic would still challenge?
5. Is the MVP done, or does one more finding need chasing?

## 6. Director dependencies (Amin)
- Azure + a **dedicated Gemini key/billing** that clears the 10k/day quota for the full run.
- Sign-off on: the fairness resolution (§2.4), the rubric change (§2.2), and the release tag.

## 7. Return format
Same as prior + paste the **per-band results tables with CIs** and the honest wins/losses summary. State plainly
whether the MVP's core thesis (cache earns its overhead) is validated, not validated, or mixed.

---
*Handoff H10 · architect: Claude · MVP finish · fix + validate · the run that answers whether the cache delivers · honest, at volume, with CIs.*
