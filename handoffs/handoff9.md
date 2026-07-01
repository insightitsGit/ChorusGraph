# Handoff 9 — Run the A/B benchmark on Azure (fair, at volume) + honest analysis

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/BENCHMARK.md`](../docs/BENCHMARK.md) (fairness — READ, incl. the new "B reasons comparably to A" rule), H8 (the rig), DESIGN §15.
**Return in:** `handoffs/handoffback9.md`.

This is **the** milestone: the first trustworthy A vs B numbers. It is worthless if rushed or rigged —
the fairness fixes in §2.1 come **before** any run.

---

## 0. Operating rules
No fakes — real Gemini, real Azure run. **Report honest wins AND losses. No winner declared without
confidence intervals.** A mixed, disclosed result is the goal, not a clean one.

## 1. Goal
Produce the first credible A/B result — cost, latency, accuracy vs LangGraph — on **Azure**, at volume,
with **B reasoning comparably to A**, plus calibrate the belief-knob thresholds from real distributions.

## 2. Deliverables (scope)

### 2.1 Fairness fixes — DO THESE FIRST (from the H8 review)
- **B runs its LLM ReAct/AgentNode path, not the regex researcher** — so the A↔B delta isolates the
  ChorusGraph cache/memory layer, not a routing shortcut A lacks. (BENCHMARK.md checklist.)
- **Rubric scores on answer content** (the H8 fix) — verify A is not penalized for correct answers.
- Confirm both, in writing, before running.

### 2.2 Run at volume on Azure
≥ **1000 tasks** (~200 sessions × 5) — H8's estimate to clear `MIN_HITS=300` for the fx slug. Persist
per-task **JSONL** + the aggregate report.

### 2.3 Repeat-rate sensitivity
Run at **20% / 40% / 60%** repeat bands (H8 §9.2). The cache benefit must be shown across realistic
repeat assumptions — not one favorable band. If it only wins at 60% and vanishes at 20%, that's a finding, report it.

### 2.4 Analysis with confidence intervals
Latency (P50/P95 + CI), cost/task (+ CI), accuracy (+ CI), cache hit-rate, per-slug FP via the shadow/replay
rig. **No point-estimate claims.**

### 2.5 Calibrate belief-knob thresholds
From the measured grounding/confidence distributions, derive thresholds for `confidence_stop` /
`groundedness_floor` (§7.5). Calibrate here; enabling in production is a later step.

### 2.6 Honest mixed report — `docs/BENCHMARK_RESULTS.md`
Where B wins, where B loses or ties, the residual A/B asymmetries (regex vs LLM if any remain, graph
depth, etc.), and CIs throughout. **No winner declaration without CIs.**

## 3. Explicitly OUT of scope
Load/traffic/throughput test (separate, director-designed) · enabling belief-knobs in production
(calibrate only) · durable Cortex · any marketing claim.

## 4. Acceptance criteria
- [ ] B reasons comparably to A (LLM path) **and** rubric scores on content — both verified before the run.
- [ ] ≥1000-task run completed on Azure; JSONL + report persisted.
- [ ] Results reported with **confidence intervals** across the 20/40/60% repeat bands.
- [ ] `BENCHMARK_RESULTS.md` discloses wins **and** losses **and** residual asymmetries.
- [ ] Belief-knob thresholds calibrated from real distributions.
- [ ] No mocks; **no winner claim without CIs.**

## 5. Open questions for handoffback9
1. Does the cache benefit hold at the **low (20%) repeat band**, or only at 60%?
2. Which slugs became `CACHEABLE` (FP < 1% at MIN_HITS)? At what hit-rate?
3. Calibrated belief thresholds — what came out?
4. **Any surprising *disadvantage* of ChorusGraph** the run surfaced? (Actively look — this is the honest half.)
5. Proposed next steps.

## 6. Director dependency (Amin)
Azure environment + Gemini key for the ~1000-task run (~$2–5, ~1.5–2h). Decide where results/JSONL persist.

## 7. Return format
Same as prior + paste the **results tables with confidence intervals** and the honest wins/losses summary.

---
*Handoff 9 · architect: Claude · the real numbers · fair + at volume + CIs · honest wins AND losses.*
