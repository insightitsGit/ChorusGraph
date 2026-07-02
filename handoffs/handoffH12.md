# Handoff H12 — Embed once: the shared vector substrate (+ 300-task volume run)

**From:** Architect (Claude, verify role) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Reference:** the vector-substrate principle (DESIGN §7.6/§13), H11 results.
**Return in:** `handoffs/handoffbackH12.md`.

**The point:** realize the intended architecture — **ONNX embeds the text ONCE per turn at ingress; every
internal component projects from that one shared 384-d vector.** Today the same message is ONNX-embedded
**3×** per turn. This is a behavior-preserving efficiency fix that matches the original vector-native design.

## 0. Operating rules
- **Behavior-preserving.** Same MiniLM 384-d → same projections → **identical outputs** (accuracy, cache
  hits, answers). If any output changes, it's a bug. This is a refactor, not a feature.
- No fakes; recorded fixtures OK for tests. Don't change projection dims (64 for cache/router, 128 for Cortex) or thresholds.

## 1. The confirmed redundancy (verified call sites)
For one turn on the same `message`, ONNX `cache._embedder.embed(...)` fires 3×:

| # | Site | Projects to |
|---|------|-------------|
| 1 | `cache_gate/gate.py:51` | 64-d (cache/router) |
| 2 | `transforms/projector.py:16` ← `nodes.py:250` (writer `project_text`) | 64-d |
| 3 | `transforms/projector.py:16` ← `nodes.py:254` → `cortex_service.py:115` (Cortex recall) | 128-d |

The **expensive** part is the MiniLM ONNX pass (~5–20 ms). The projection (384→64 / 384→128) is a **matmul
(µs)**. The 384-d raw embed is **tenant-agnostic** and identical across all three — so it should be computed
once and reused; only the (cheap, tenant-seeded) projections differ.

## 2. Deliverables

### 2.1 Embed once at ingress → shared `raw_384` on the state
At the start of a turn, compute `raw_384 = cache._embedder.embed(message)` **once**; put it on the state
(e.g. a `VectorContext`/state field). Tenant-agnostic, so it's valid for every downstream component.

### 2.2 Every internal component projects from the shared vector — no re-embed
Refactor the three sites to **accept a precomputed `raw_384`** and skip embedding:
- `project_text(cache, text, raw_384=None)` — use the passed vector if present (else embed, for back-compat).
- `gate(...)` — accept `raw_384`; project to 64-d, don't re-embed.
- `recall_structured(...)` — accept/pass `raw_384`; Cortex applies its own 384→128 projection.
- Thread `raw_384` through `nodes.py` (250 + 254) and the cache_gate call.
Also share the **64-d** projection between the cache_gate and the writer hop (same dim, same projector).

### 2.3 Enforce the boundary rule
ONNX embed happens **only at ingress**. Add an **instrumented counter** on the embedder (count `embed()`
calls per turn) and a **test that fails if it fires more than once** per turn on the finance path.

### 2.4 Regression gate — small run FIRST, must match exactly (do this before the volume run)
Re-run the **same small workload** (the 40/60-task pilot, **same seed** as the prior run) on the refactored
code and assert **identical** accuracy, cache-hit-rate, and **per-task answers** vs the pre-refactor baseline
(`h11_fixed_a_60`). **Diff the per-task answers, not just the aggregates.**

**This is a HARD GATE:** if *anything* differs, STOP and fix the refactor — do **NOT** run the 300-task
volume until the small regression is byte-clean. The whole point of H12 is "same outputs, computed once."

### 2.5 Measure the savings (honest)
Report embeds/turn (before 3 → after 1) and the **latency delta**, especially on **cache hits** (where the
turn is embed-dominated). Note: the saving is **CPU/latency + throughput** (ONNX is local/free) — **not**
LLM cost. Real and meaningful at scale and on hits; modest on LLM-bound misses. State it accurately.

### 2.6 Then: the 300-task volume run (on the fixed code)
**Only after the §2.4 small regression gate passes byte-clean,** run **≥300 tasks, bands 20/40/60**, post-fix A (from H11), paired, with CIs → clears the
`MIN_HITS=300` bar **and** shows the embed-once latency win at volume. Update `docs/BENCHMARK_RESULTS.md`.

## 3. Out of scope
Enterprise E1–E9 · changing projection dims or thresholds · new features · anything that alters outputs.

## 4. Acceptance criteria
- [ ] ONNX `embed()` fires **exactly once** per finance turn (proven by the instrumented counter + a test).
- [ ] cache_gate, writer `project_text`, and Cortex recall all consume the shared `raw_384`; no internal re-embed.
- [ ] **Small-workload regression gate run FIRST** and passes **identical** (accuracy, cache-hit, per-task answers) vs `h11_fixed_a_60` — the 300-task run is **not** started until this is clean.
- [ ] Latency/throughput saving measured + reported (embeds 3→1; hit-latency delta).
- [ ] 300-task run (bands 20/40/60) on the fixed code, with CIs; `MIN_HITS=300` addressed.
- [ ] No fakes; prior tests green; no dim/threshold changes.

## 5. Open questions for handoffbackH12
1. Did any Prism lib (PrismCache/Cortex) require an upstream change to accept a precomputed embedding, or did the ChorusGraph-side threading suffice?
2. Measured latency saving per turn — and on cache hits specifically?
3. Confirm outputs are byte-identical to H11 (or explain any delta).
4. 300-task frontier: cache hit-rate + `(h, FP)` per band; any slug now `CACHEABLE` (n≥300)?

## 6. Return format
Summary · file tree · how to run · embed-count proof · before/after latency · **identical-output regression proof** · 300-task tables with CIs · decisions/deviations · blockers.

---
*Handoff H12 · embed once, project many · realize the vector substrate · behavior-preserving · + volume run to close the MVP.*
