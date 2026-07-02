# Handoff H13 — Multi-agent benchmark (C vs D, healthcare): the vector-substrate thesis

**From:** Architect (Claude, verify role) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Reference:** `docs/BENCHMARK.md` (fairness), the multi-agent design (DESIGN §7.6/§7.7), CHORUS/PrismLang.
**Return in:** `handoffs/handoffbackH13.md`.

**The point.** A/B was **single-agent** — it never exercised ChorusGraph's biggest differentiator: the
**vector substrate + fast M2M communication** in *multi-agent* systems. H13 adds **C vs D** in **healthcare**:
- **C = a competent multi-agent healthcare app on LangGraph** (baseline).
- **D = the same app on ChorusGraph** (vector hops / PrismLang envelope, role-typed agents, cache, Cortex).
Same app, same agents, same tools, same model — **only the framework differs.**

## 0. Operating rules — fairness is even more critical here
- **Learn from the A disaster.** In A/B, Container A never called its tools and we almost shipped a mirage.
  In a *multi-agent* baseline the failure surface is bigger (agents that don't hand off, don't call tools,
  or lose state). **C must be a genuinely competent LangGraph multi-agent build.** A fair-baseline audit is required.
- **Only the framework differs.** Identical agents/roles, tools, prompts, model, task set, KB.
- **No rigging.** Win by D's real capability, not by a weak C. Improve D's code to win, never hobble C.
- No fakes — real Gemini, real tools/KB.

## 1. The healthcare multi-agent app (same graph in C and D)
A clinical-decision-support pipeline (supervisor + specialists):
1. **Intake** — parse patient case (symptoms, meds, history).
2. **Retrieve** — pull relevant clinical guidelines (real KB / pgvector).
3. **Analyze** — reason over symptoms + guidelines.
4. **Drug-interaction** — check meds via a real interaction dataset/tool.
5. **Safety validator** — flag red-flags; **abstain if ungrounded** (grounding gate).
6. **Writer** — compose the recommendation with citations.

Same node/role structure in both. In **D** these are role-typed agents (§7.7) exchanging the **PrismLang
vector envelope** between hops; in **C** they pass LangGraph text/JSON state.

## 2. The experiment that proves the thesis (the key metric)
The single-agent case can't show the vector-substrate win — it appears **as the number of agents/hops grows.**
So **vary the pipeline depth (e.g. 2 → 4 → 6 agents)** and measure how cost/latency scale:

- **Primary chart:** total tokens + cost + latency **vs number of agents/hops**, for C and D.
- **The thesis, made falsifiable:** D's per-task cost/latency should stay **flatter** as agents are added
  (vector hops ~constant size, no re-reading the growing transcript), while C's **grows** (each agent
  re-reads history as prompt tokens). If D does *not* diverge from C as depth grows, the thesis fails —
  report that honestly.

Secondary: task accuracy, and **safety abstention** (does D refuse-when-ungrounded where C hallucinates —
the healthcare-critical differentiator).

## 3. Scope: single-process first (CHORUS is Phase 2)
- **H13 = single-process multi-agent.** Both C and D run all agents in one process. This tests the
  **vector-substrate / PrismLang token+latency savings** — CHORUS is **not** exercised here.
- **Phase 2 (later, distributed):** split D's agents across processes/containers so **CHORUS** carries the
  vectors — that tests the transport story (179ms transatlantic, 4.45× bandwidth, no tokenization boundary).
  **Flag it, don't build it in H13.** (Note in the doc that the single-process result understates D's full
  advantage precisely because CHORUS isn't in play yet.)

## 4. Deliverables (build the rig + prove it works — do NOT draw conclusions)
- `benchmark/container_c/` — LangGraph multi-agent healthcare app (competent baseline + `FAIR_BASELINE_C.md`).
- `benchmark/container_d/` — ChorusGraph multi-agent version (vector hops, role agents, cache, Cortex).
- `benchmark/healthcare_workload.py` — real clinical cases (incl. safety-critical cases that *should* abstain);
  document the case model; support **depth sweep** (2/4/6 agents).
- **Shared measurement** — identical schema; add **per-hop** token/latency (to see the compounding).
- `benchmark/run_multiagent.py` — harness with the depth sweep.
- **Small dry-run** (e.g. 10–20 cases at each depth) proving both C and D run end-to-end with real Gemini,
  **and that C's agents actually call tools and hand off** (the anti-A-bug gate).

## 5. Explicitly OUT of scope
Distributed CHORUS variant (Phase 2) · enterprise E-track · drawing conclusions / full-scale run (that's the
run handoff, gated on quota) · any "D beats LangGraph" claim.

## 6. Acceptance criteria
- [ ] C is a **competent** LangGraph multi-agent build — agents call tools **and hand off correctly**
      (verified: non-zero tool calls + real inter-agent state flow, per the fair-baseline audit).
- [ ] Only the framework differs (identical agents/tools/prompts/model/cases/KB — checklist in handoffback).
- [ ] Both C and D run the healthcare pipeline end-to-end on a dry-run with real Gemini.
- [ ] Measurement captures **per-hop** cost/latency + a **depth sweep (2/4/6 agents)**.
- [ ] Safety abstention is measured (grounding gate fires on ungrounded cases).
- [ ] No fakes; no rigging; prior tests green. **No conclusions drawn — rig + dry-run only.**

## 7. ⚠️ Quota reality
Multi-agent burns **N× more LLM calls per task** (one per agent) — the Gemini 10k/day quota (which already
throttled H9/H10/H12) will bite **harder** here. **Size the dry-run small**, and the full depth-sweep run is
**gated on real quota headroom** (paid tier / Azure billing). Do not attempt the full run on the free key.

## 8. Open questions for handoffbackH13
1. C fair-baseline audit — where might a LangGraph expert say the multi-agent baseline is weak?
2. Real KB + drug-interaction data source used?
3. Dry-run: does D's per-hop cost stay flatter than C's as depth grows (directional signal)?
4. Quota: how many cases × depths can a full run afford, and what quota is needed?
5. Proposed scope for the full run + the Phase-2 (CHORUS distributed) variant.

## 9. Return format
Summary · file tree · how to run · dry-run output (both C and D, per-hop numbers, C tool-calls proven) ·
fair-baseline audit for C · decisions/deviations · blockers · answers to §8 · proposed full-run scope.

---
*Handoff H13 · multi-agent C vs D (healthcare) · tests the vector-substrate thesis A/B never could · fair baseline first · single-process now, CHORUS later · quota-gated.*
