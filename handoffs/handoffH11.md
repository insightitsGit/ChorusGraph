# Handoff H11 — Fix the broken baseline (Container A never calls tools) + honest rerun

**From:** Architect (Claude, verify role) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Reference:** handoffbackH10, `docs/BENCHMARK.md` (fairness), `benchmark/container_a/graph.py`.
**Return in:** `handoffs/handoffbackH11.md`.

**⚠️ Read this first — the point of H11.** The mission is to make **ChorusGraph (B) genuinely the best** — and
to get there we use *honest* measurement to find and fix B's real weaknesses. Right now we can't even see them,
because **Container A is broken: it never calls the FX tool**, so the H10 "B 82% vs A 27%" is a mirage. So H11
is two moves: **(1) fix A into a competent baseline so B's true gaps become visible, then (2) for every place B
loses, ties, or fails a task — diagnose why and REWIRE/FIX B until it wins on the merits.** A fair A is not the
enemy of winning — it's the map that shows exactly what to improve in B. A rigged win hides the bugs we need to fix.

## 0. Operating rules (careful — non-negotiable)
- No fakes; real Gemini, real tools. Real prior tests stay green.
- **Win by making B genuinely better, not by making A worse.** Improve B's *real capability* (rewire the code);
  do NOT hobble A, game the rubric, or lower thresholds to manufacture a win — a fake win hides the weaknesses
  we're trying to fix. The only change to A is: make it actually call its tools (a fair baseline).
- **No external accuracy/latency claim until the fixed-A rerun.** The current numbers are off a broken baseline.

## 1. The evidence (verified from the JSONL)
In `benchmark/results/h10_slices_pilot_60/band_40_container_a.jsonl`:
- **All 47 FX tasks: `tool_calls = 0`.** A never invokes `fetch_exchange_rate`.
- A's answers literally say: *"I cannot provide real-time exchange rates…"*, *"…no tool results have been
  provided,"* *"My current information only includes the USD to GBP exchange rate"* (a **stale** pair from a
  prior turn), and one hallucinated *"0.79 … as of October 27, 2023, per the ECB."*
- Scoring is **fair** — `benchmark/measure.py:score_task_success` runs the identical rubric for A and B
  (confirmed). So this is **not** a rubric problem. A simply never calls the tool.

## 2. Root cause (localized in `container_a/graph.py`)
A's `react_node` / `route_after_react` send **react → writer without ever hitting `tool_node`** whenever the
model's first ReAct response has no parseable action:
- Lines 81–82: `finish=true` + no action → `react_done=True` → writer (no tool).
- Lines 87–88: `if not has_action and not finish and scratchpad: react_done=True` — and `route_after_react`
  (line 164) **falls through to `"writer"`** when there's no `pending_action`.
- Likely compounded by **stale session state**: MemorySaver + `thread_id` can carry a prior turn's
  `scratchpad`/`tool_result` into a new question, so react "finishes early" and the writer references the
  **wrong pair** ("only includes USD to GBP").

## 3. Deliverables

### 3.1 Diagnose precisely (before fixing)
Run **one** FX task through A and log: the raw ReAct JSON, `has_action`, `pending_action`, the route taken,
and the incoming session state. Confirm whether it's (a) the model not emitting an action, (b)
`parse_react_json` failing, or (c) stale session scratchpad. State which in the handoffback.

### 3.2 Fix Container A → a competent baseline
Make A **reliably call `fetch_exchange_rate`** on FX questions and ground the answer in the tool rate:
- Ensure a fresh FX question routes react → **tool** → writer (not straight to writer).
- Ensure each new question fetches **its own** pair, not a stale prior pair (clear/scope per-turn react state).
- (Optional, if it mirrors B fairly) a "must call a tool before answering" guard — but only if B has the
  equivalent; otherwise leave A as plain ReAct. Do not give A an advantage B lacks either.
- **Acceptance gate: A shows `tool_calls ≥ 1` on FX tasks, and A's FX answers contain the correct tool rate.**

### 3.3 Honest rerun → diagnose → REWIRE B to win on the merits
Rerun the same workload + seed as `h10_slices_pilot_60`; report fixed-A vs B **with CIs**. This is the
*diagnostic* run — it shows where B **genuinely** wins and where B still loses, ties, or fails tasks. Then,
**for every place B doesn't clearly win, and every task B fails, find the root cause and fix B's real
capability** (not the measurement):
- B fails where A now succeeds → why (tool routing, missed cache, weak template/recall) → **rewire that path in B.**
- B ties/loses on cost, latency, or accuracy → find the overhead/gap → **close it in B's code.**
- Iterate: rerun → re-diagnose → re-fix, until B wins honestly on the slices that matter (FX, memory), or a
  remaining gap is a genuine hard tradeoff you then document.
The win must be **earned in B's code, verified against the fair A.** Log each B fix with a before/after number.

### 3.4 Held-out paraphrase test (validate B's cache is real generalization)
The H10 67% paraphrase hit-rate may reflect **multi-phrase pre-seeding** (all canonical phrasings seeded after
the tool), not semantic generalization. Prove which: **seed phrasing set S, evaluate on a DISJOINT set T of
unseen paraphrases.** Report the hit-rate on T separately. That isolates "semantic cache generalizes" from
"we pre-loaded the phrasings."

### 3.5 (Recommended) Volume to clear the bar
≥300-task band-40 (and 60) post-fix, both containers, to clear `MIN_HITS=300` and tighten CIs — turns "pilot"
into "validated."

### 3.6 Docs
Update `docs/BENCHMARK_RESULTS.md` + `FAIRNESS_H9.md`: mark the **pre-fix A numbers INVALID (broken baseline)**,
add the fixed-A comparison + the held-out paraphrase result. No claim survives that isn't from the fixed run.

## 4. Out of scope
Enterprise track (E1–E9) · production belief-knobs · Azure migration · lowering thresholds · anything that
changes the result other than making A competent.

## 5. Acceptance criteria
- [ ] Root cause of A-not-calling-tools stated (a/b/c).
- [ ] A shows `tool_calls ≥ 1` on FX tasks and grounds answers in the tool rate (broken baseline fixed).
- [ ] Fixed-A vs B rerun reported with CIs; pre-fix A numbers marked invalid.
- [ ] Every place B loses/ties/fails is diagnosed, and B's capability **rewired** to win on the merits — each fix logged before/after (win earned in B's code, not the measurement).
- [ ] Held-out paraphrase hit-rate reported (semantic generalization isolated from seeding).
- [ ] No hobbling A / tuning B / rubric changes to shift the result (state that none were made).
- [ ] Prior tests green; no fakes.

## 6. Open questions for handoffbackH11
1. Root cause of A never calling tools (a/b/c)?
2. Fixed-A FX accuracy — and the honest B-vs-A delta now. Does B still win, and where?
3. Held-out paraphrase hit-rate — is the semantic cache real or seeded?
4. Any metric where fixing A flipped the result?

## 7. Return format
Summary · file tree · how to run · fixed-A vs B tables **with CIs** · held-out paraphrase result · what
changed in A (and confirmation nothing was done to tilt the result) · honest wins/losses · blockers.

---
*Handoff H11 · fix the broken baseline so B's real gaps show · then rewire B to win on the merits · earned, not rigged.*
