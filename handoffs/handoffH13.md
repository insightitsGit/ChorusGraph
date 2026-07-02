# Handoff H13 — Close the MVP (Cortex fix + volume) + Multi-agent C vs D (healthcare)

**From:** Architect (Claude, verify role) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Reference:** handoffbackH12, `docs/BENCHMARK.md` (fairness), multi-agent design (DESIGN §7.6/§7.7), CHORUS/PrismLang.
**Return in:** `handoffs/handoffbackH13.md`.

Two parts: **A) finish the outstanding MVP items** (the Cortex 128-d check + the volume run that quota blocked),
then **B) the multi-agent C-vs-D healthcare benchmark** — the test that proves the vector-substrate thesis A/B never could.

## 0. Operating rules (apply every lesson)
- **Fairness is sacred.** A/B nearly shipped a mirage because Container A was broken (never called tools). In a
  *multi-agent* baseline the failure surface is bigger — **C must be a genuinely competent LangGraph build.**
- Only the framework differs. **Win by D's real capability, never by hobbling C.** No rigging, no rubric games.
- No fakes — real Gemini, real tools/KB. Behavior-preserving refactors stay behavior-preserving.
- **Quota-aware:** the Gemini 10k/day cap throttled H9/H10/H12; multi-agent burns it faster. Size runs accordingly.

---

# PART A — Finish the MVP

## A1. Cortex 128-d verification / fix (from the H12 review)
H12's embed-once refactor proved the **64-d cache path** unchanged (cache-hit 0.414 → 0.414, identical). But
Cortex's native projection is **128-d** (it uses 128 because 64 "crowds at scale"), and the handoffbackH12
diagram said *"Cortex uses shared 64-d."* The one `task_success` flip (task-0026) was a **Cortex** task.

- **Verify** Cortex still projects to its **native 128-d** from the shared `raw_384` — **not** silently
  downgraded to the shared 64-d.
- If it *was* downgraded → **fix it** (Cortex applies its own 384→128 projection from `raw_384`); re-run the
  60-task regression and confirm the Cortex/memory tasks match H11.
- **Acceptance:** Cortex recall runs at 128-d; memory-task results equivalent to `h11_fixed_a_60` (the one
  flip explained as LLM variance, not a dim change).

## A2. The 300-task volume run (still open — quota blocked in H12)
H12's volume run only got **~90 tasks on band 20**; **bands 40/60 never ran** (quota). The `MIN_HITS=300` bar
is still not cleared → "validated at volume" remains open.

- Run **≥300 tasks, bands 20/40/60**, post-fix A (H11) + embed-once D (H12), paired, with CIs.
- **Gated on real quota** (paid Gemini tier / Azure billing / higher-cap key). **Do not attempt on the free key
  — it will throttle again.** If quota isn't available yet, say so and leave A2 pending; A1 and Part B don't depend on it.
- Report per-band cache hit-rate + `(h, FP)`; note any slug now `CACHEABLE` (n≥300). Update `docs/BENCHMARK_RESULTS.md`.

## A3. Release marker (optional)
Tag `v0.9.1` (or `v0.10.0`) once A1 passes and the Director approves the push.

---

# PART B — Multi-agent benchmark: C vs D (healthcare)

A/B was single-agent — it never exercised the **vector substrate + fast M2M communication**, ChorusGraph's
biggest differentiator. C vs D tests it.
- **C = a competent multi-agent healthcare app on LangGraph** (baseline, text/JSON state between agents).
- **D = the same app on ChorusGraph** (PrismLang vector envelope between hops, role-typed agents, cache, Cortex).
Same app, agents, tools, model, cases — only the framework differs.

## B1. The healthcare pipeline (identical in C and D)
Supervisor + specialists: **Intake → Retrieve (real guideline KB/pgvector) → Analyze → Drug-interaction (real
dataset/tool) → Safety-validator (abstain if ungrounded) → Writer (cited recommendation).** In D these are
role-typed agents (§7.7) exchanging the vector envelope; in C they pass LangGraph text state.

## B2. The experiment that proves the thesis
The vector-substrate win only appears **as agents/hops grow**. So **sweep pipeline depth (2 → 4 → 6 agents)**:
- **Primary chart:** total tokens + cost + latency **vs number of agents**, for C and D.
- **Falsifiable thesis:** D should stay **flatter** as depth grows (vector hops ~constant, no re-reading the
  growing transcript); C **grows** (each agent re-reads history as prompt tokens). **If D doesn't diverge from
  C as depth increases, the thesis fails — report that honestly.**
- Secondary: accuracy, and **safety abstention** (D refuses-when-ungrounded where C hallucinates — the
  healthcare-critical differentiator).

## B3. Scope: single-process now, CHORUS later
- **H13 = single-process** multi-agent (all agents one process). Tests the **PrismLang vector-hop** savings;
  **CHORUS is NOT exercised.** Note in the doc that this **understates** D's full advantage.
- **Phase 2 (flag, don't build):** distributed variant — D's agents across processes/containers so **CHORUS**
  carries the vectors (tests transport: 179ms transatlantic, 4.45× bandwidth, no tokenization boundary).

## B4. Deliverables (build the rig + dry-run — no conclusions)
- `benchmark/container_c/` — LangGraph multi-agent healthcare app + `FAIR_BASELINE_C.md`.
- `benchmark/container_d/` — ChorusGraph multi-agent version.
- `benchmark/healthcare_workload.py` — real clinical cases (incl. safety-critical → should abstain); depth sweep (2/4/6).
- **Shared measurement** with **per-hop** token/latency (to see the compounding).
- `benchmark/run_multiagent.py` — harness with the depth sweep.
- **Small dry-run** (10–20 cases per depth) proving both run end-to-end AND **C's agents actually call tools and
  hand off** (the anti-A-bug gate).

---

## Acceptance criteria
**Part A**
- [ ] Cortex verified at native **128-d** (or fixed); memory tasks equivalent to H11.
- [ ] Volume run ≥300 tasks bands 20/40/60 with CIs — **or** explicitly marked pending on quota.

**Part B**
- [ ] C is a **competent** LangGraph multi-agent build — agents call tools **and hand off** (verified, per fair-baseline audit).
- [ ] Only the framework differs (identical agents/tools/prompts/model/cases/KB).
- [ ] C and D run the pipeline end-to-end on a dry-run with real Gemini.
- [ ] Measurement captures **per-hop** cost/latency + **depth sweep (2/4/6)**.
- [ ] Safety abstention measured.
- [ ] No fakes; no rigging; prior tests green. **No conclusions drawn — rig + dry-run only.**

## Open questions for handoffbackH13
1. Cortex: was it 128-d or downgraded to 64-d? Fixed?
2. Volume run: ran, or pending on quota? If ran, per-band cache + `(h,FP)`.
3. C fair-baseline audit — where might a LangGraph expert call it weak?
4. Dry-run: does D's per-hop cost stay flatter than C's as depth grows (directional)?
5. Quota needed for the full multi-agent run; proposed full-run + Phase-2 (CHORUS) scope.

## Return format
Summary · file tree · how to run · Part A results (Cortex + volume/pending) · Part B dry-run (C+D per-hop, C
tool-calls proven, fair-baseline audit) · decisions/deviations · blockers · answers to open questions.

---
*Handoff H13 · A) close the MVP (Cortex 128-d + volume) · B) multi-agent C vs D healthcare — the vector-substrate thesis · fair baseline first · single-process now, CHORUS later · quota-gated.*
