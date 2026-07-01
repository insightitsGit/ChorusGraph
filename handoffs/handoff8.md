# Handoff 8 — Build the A/B Benchmark Rig (fair baseline + workload + measurement)

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/BENCHMARK.md`](../docs/BENCHMARK.md) (READ FIRST — the fairness rules are the point), DESIGN §15.
**Builds on:** H4–H7 (the ChorusGraph finance agent = Container B). **Return in:** `handoffs/handoffback8.md`.

---

## 0. Operating rules
No fakes — real Gemini, real tools. **Build the rig; do NOT draw conclusions yet** (running at scale +
analysis is H9). The deliverable is a *fair, runnable* A-vs-B rig, not a result. **The fairness rules in
`BENCHMARK.md` are non-negotiable — a rigged baseline makes this whole handoff worthless.**

## 1. Goal

Build a **fair, runnable A/B rig**: Container A (the finance agent on **LangGraph**, a *competent*
baseline) + Container B (the existing ChorusGraph agent) + a **realistic finance workload** + **identical
measurement** in both. Per `BENCHMARK.md`.

## 2. Deliverables (scope)

### 2.1 Container A — LangGraph baseline — `benchmark/container_a/`
The **same** finance agent on plain LangGraph: same Frankfurter/`compound_interest` tools, same prompts,
same Gemini model, same KB, LangGraph's own checkpointer + a standard ReAct. **No ChorusGraph.** This must
be a *reasonable* LangGraph build — include a short **fair-baseline note** justifying the design choices
(a LangGraph-literate reviewer should nod, not wince).

### 2.2 Container B — ChorusGraph — `benchmark/container_b/`
The existing ChorusGraph finance agent (H4–H7), wired to emit the **same measurement schema** as A.
Cache thresholds come from the **measured** shadow frontier — **NOT** the H4 demo thresholds (0.82/0.85).

### 2.3 Shared measurement — `benchmark/measure.py`
Identical per-task logging in both: `latency_ms, llm_calls, tokens_in, tokens_out, cost_usd,
task_success, answer` (+ B-only `cache_hit, cache_score, grounding_score`). One schema, both containers.

### 2.4 Workload generator — `benchmark/workload.py`
A **realistic** finance query set with a documented **repeat/paraphrase model** (some queries recur, some
paraphrased, some novel) and **controllable volume** (large enough to clear `MIN_HITS=300` per slug).
Document the repeat model so its realism can be defended.

### 2.5 Benchmark harness + dry-run — `benchmark/run.py`
Runs the workload through both containers, collects measurements, emits a comparison report skeleton. Prove
it works end-to-end on a **small dry-run** (e.g. 20 tasks) — real Gemini, both containers, identical schema.

## 3. Explicitly OUT of scope
Running the full-scale benchmark + drawing conclusions (H9, on **Azure**) · enabling belief-knobs (needs
H9 calibration) · durable Cortex · hand-tuning B to win (forbidden — see BENCHMARK.md) · any "we beat
LangGraph" claim.

**Scope boundary — NOT a load test.** This measures **per-task** cost/latency/accuracy on a controlled
workload. Production-scale concurrent **load/traffic/throughput** is a *separate* future test (director
will design it). Keep the workload about **repeat-rate realism** (to exercise the cache), NOT concurrency.

## 4. Acceptance criteria
- [ ] Container A is a **competent** LangGraph build of the same agent, with a fair-baseline note.
- [ ] Only the framework differs — model/tools/prompts/KB/workload identical across A and B (checklist in handoffback).
- [ ] Both containers emit the **identical** measurement schema.
- [ ] Workload generator produces a realistic, documented, volume-controllable query set.
- [ ] A **20-task dry-run** runs end-to-end through both containers with real Gemini and collects comparable measurements.
- [ ] B's cache thresholds are the **measured** ones, not the H4 demo values.
- [ ] No mocks; `pytest` green. **No benchmark conclusions drawn — rig only.**

## 5. Open questions for handoffback8
1. Your Container A design + the fair-baseline justification — where might a LangGraph expert object?
2. The repeat/paraphrase model you used for the workload — is it defensibly realistic?
3. Dry-run comparison: any schema mismatch or measurement asymmetry between A and B?
4. What volume does a full run need to clear MIN_HITS=300 per slug? (H9 runs on **Azure** — director decision — for a true test; size the workload for that.)
5. Proposed H9 scope (run at scale, analyze, calibrate belief knobs).

## 6. Return format
Same as prior: summary · file tree · how to run · dry-run output (a few tasks through **both** A and B with
the measurement rows) · decisions/deviations · **the fairness checklist, filled in** · blockers · answers to §5 · proposed H9.

---
*Handoff 8 · architect: Claude · build the fair A/B rig · fairness is the deliverable · NO conclusions yet.*
