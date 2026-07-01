# Handoff 2 — Safe Cache Gate + Shadow-Mode False-Positive Measurement

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/DESIGN_v0.2.md`](../docs/DESIGN_v0.2.md) §8 (make-or-break), §6 (sections), §15 (metrics). Also [`../docs/WORKFLOW.md`](../docs/WORKFLOW.md) step ④.
**Builds on:** Handoff 1 (the Route Ledger — you will populate its `cache_hit`/`cache_score` slots).
**Return in:** `handoffs/handoffback2.md`.

This handoff **is** ADR-002 in executable form: the exact cache-gate algorithm + the measurement protocol.

---

## 0. Operating rules (unchanged from H1)
No fakes — real `prismlang`, real `prismcache`, real embedder; real Gemini only if unavoidable. Adapter-first (don't reimplement LangGraph). Don't modify hub code. Stay in scope. Report reality in the handoffback.

## 1. Goal

Prove — with a **measured false-positive rate** — that the cache is safe before it is ever allowed to skip an LLM call. That means building the **two-stage gate** and running it in **shadow mode** (decides, logs, but does **not** act) so we can measure the hit-rate `h` and false-positive rate `FP` per taxonomy slug and per verify-threshold. This produces the number the whole cost thesis depends on (§15).

## 2. Why this slice (context)

Today's cache decides in coarse 64-d at `constructive_score ≥ 0.88` — good for *finding candidates*, not for *authorizing a skip* (§8). A wrong skip ships a confidently-wrong answer. We do **not** turn the cache on for real until shadow mode shows `FP < budget`.

## 3. Deliverables (scope)

### 3.1 Two-stage cache gate — `chorusgraph/cache_gate/`
Implement `gate(query, section, cache) -> Decision` per the algorithm in §5. Wraps **real** PrismCache; adds the Stage-2 full-precision verify and the policy gate. Does not modify PrismCache.

### 3.2 Section schema — `chorusgraph/sections/`
A **Pydantic** `Section` model: `section_id`, `category_slug`, `content`, `vector` (64-d), `cache_policy` (`no_cache | semantic | exact | replay_safe`). (Decision: Pydantic at the section boundary; graph `State` stays TypedDict — see DESIGN §17 #5.)

### 3.3 Ledger instrumentation
Populate the H1 ledger's `cache_hit` and `cache_score` on the relevant step when the gate runs (fields already exist, always null today).

### 3.4 Embedder fail-loud guard — `chorusgraph/policy/embedder_guard.py`
Per your H1 finding (Q5): PrismCache silently falls back to the non-semantic `HashEmbedder`. **A shadow measurement run on HashEmbedder is worthless.** Ship a guard that refuses to run the gate unless a real `SentenceTransformerEmbedder` is active (env override `CHORUSGRAPH_ALLOW_HASH_EMBEDDER=1` for explicit opt-in only) + a startup canary (embed a known-similar pair, assert cosine > 0.5).

### 3.5 Shadow-mode harness + measurement — `chorusgraph/shadow/`
Per §6. Runs the gate over a **real labeled dataset**, logs would-serve vs ground-truth, aggregates `h` and `FP` per slug and per verify-threshold. Emits a report.

### 3.6 Real labeled dataset — `chorusgraph/shadow/dataset/`
**Not mocked.** Build ~60–120 *real* queries grouped by intent (paraphrase clusters + deliberate near-miss pairs that look similar but need different answers — those are the false-positive traps). Label which pairs SHOULD be cache-equivalent. Embeddings/projection are real. This is the local proxy; the production run happens on Azure (§7).

## 4. Explicitly OUT of scope
Postgres steps normalization / ADR-003 migration · OTel exporter · adapter edge-semantics cleanup · PrismCheckpointer · HITL · Cortex · native DSL/engine · turning the cache **on** in any real graph (shadow only). All later.

## 5. The gate algorithm (ADR-002 core — implement exactly this shape)

```
def gate(query, section, cache) -> Decision:
    # Stage 0 — policy
    if section.cache_policy == NO_CACHE:            return MISS

    # Stage 1 — coarse recall (existing PrismCache, 64-d)
    raw = embedder.embed(query)                     # 384-d, REAL embedder (guarded)
    env = projector.project(raw)                    # 64-d tenant-seeded
    cand = cache.recall(env, top_k=5)               # constructive_score
    top = cand[0] if cand else None
    if top is None or top.constructive_score < COARSE_THRESHOLD:   # e.g. 0.88
        return MISS
    if top.category_slug != section.category_slug:  # taxonomy guard (cross-category)
        return MISS

    # Stage 2 — full-precision verify (384-d, pre-projection)
    verify = cosine(raw, top.raw_embedding_384)     # NOT the 64-d projection
    if verify < VERIFY_THRESHOLD:                   # sweep this in shadow: 0.90..0.99
        return MISS

    # Stage 3 — policy-gated reuse
    if section.cache_policy == EXACT:        return HIT_REUSE(top.value)
    if section.cache_policy == REPLAY_SAFE:  return HIT_REVALIDATE(top.value)
    if section.cache_policy == SEMANTIC:     return HIT_AS_CONTEXT(top.value)  # never verbatim
```

**Implementation question you must resolve (report it):** Stage 2 needs the candidate's **raw 384-d embedding**. Does PrismCache expose/persist it, or must ChorusGraph store the 384-d vector alongside the cache entry itself? Pick one, justify it, and note the storage cost.

## 6. Shadow-mode protocol (the measurement)

For each query in the dataset:
1. Compute `gate(...)` — **log the decision; do NOT serve it.**
2. Obtain ground truth: for `exact`/`replay_safe` sections (route, retrieval-set), the label / a fresh deterministic recompute. For `semantic` (generative) sections, mark **ineligible-for-verbatim** — they never count as a served hit, so exclude from the FP numerator this slice (generative-answer comparison via LLM-judge is a follow-up; note it).
3. `verdict = compare(would_serve, truth)` — exact/structural match for deterministic sections.
4. Record to the ledger + a `shadow_results` table: `query, slug, coarse_score, verify_score, decision, verdict`.

**Aggregate and report**, per slug and per `VERIFY_THRESHOLD ∈ {0.90, 0.93, 0.95, 0.97, 0.99}`:
- `h` = hit-rate = fraction of queries the gate would serve
- `FP` = false-positive rate = fraction of *would-serve* cases where `verdict = mismatch`
- The `(h, FP)` frontier → the threshold where `FP < 1%` at the highest `h`.

This frontier is the deliverable. It directly answers §15's open metric.

## 7. Data realism (be honest about it)
The local dataset is a **proxy** — real embeddings, real cache, but not production traffic. The **real** number comes from replaying **real Dashboard/Website Hub traffic on Azure** (director-run). So: the **mechanism + a preliminary local frontier** is what Handoff 2 delivers; the production frontier is the Azure follow-on. State this plainly in the report — do not present the local number as production.

## 8. Acceptance criteria
- [ ] `gate()` implements the exact §5 shape; Stage 2 verifies on 384-d, not 64-d.
- [ ] Embedder guard blocks HashEmbedder unless explicitly opted in; canary asserts a real embedder.
- [ ] Shadow run over the real dataset produces a per-slug, per-threshold `(h, FP)` table.
- [ ] Ledger `cache_hit`/`cache_score` populated when the gate runs.
- [ ] Nothing is ever served from cache in a live path (shadow only).
- [ ] No mocks/fakes; real prismlang/prismcache/embedder.
- [ ] `pytest` green; report pasted in the handoffback.

## 9. Open questions to answer in handoffback2
1. Stage-2 raw-embedding source: PrismCache-exposed or ChorusGraph-stored? Storage cost?
2. The `(h, FP)` frontier you measured locally — and which threshold hits `FP < 1%`.
3. Where did near-miss pairs slip through (the actual false positives)? Characterize them — that tells us if 384-d verify is enough or if we need the taxonomy/token check harder.
4. Recommended default `COARSE_THRESHOLD` / `VERIFY_THRESHOLD` for the Azure run.
5. Proposed scope for Handoff 3.

## 10. Return format
Same as H1 §7: summary · file tree · how to run · **real** test + measurement output (paste the `(h, FP)` table) · decisions/deviations · blockers · answers to §9 · design contradictions · proposed H3 scope.

---
*Handoff 2 · architect: Claude · design v0.2 · ADR-002 in executable form · shadow measurement only, cache never served live.*
