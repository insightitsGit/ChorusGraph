# Handoff 3 — Production Shadow Replay: the real (h, FP) frontier

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/DESIGN_v0.2.md`](../docs/DESIGN_v0.2.md) §8, §15. Builds directly on Handoff 2 (reuse the `gate()` + shadow harness — do not rewrite them).
**Return in:** `handoffs/handoffback3.md`.

---

## 0. Operating rules (unchanged)
No fakes — real `prismlang`/`prismcache`/embedder, real logs. Shadow only (never serve). Report reality, including negative results.

## 1. Goal

Produce the **real** `(h, FP)` frontier by replaying **production hub traffic** through the H2 gate — and do it with **statistical honesty** so we never bless a threshold on insufficient data. This is the go/no-go for the entire cost thesis. The H2 local result (FP=0 on ~2–7 hits) proves the rig works and *nothing* about safety; this handoff replaces the proxy with real volume.

## 2. Why this slice (context)

The core product claim — "we cut LLM cost by safely reusing answers" — is currently **unvalidated**. A checkpointer, HITL, Cortex, etc. are all premature until we know the cache is real. This handoff answers the one question that gates everything: *at a threshold where FP < 1%, how high is the hit rate on real traffic?*

## 3. Deliverables (scope)

### 3.1 Query-log ingest — `chorusgraph/shadow/replay/`
- **Real source (confirmed in code):** the hubs already persist every turn to Postgres.
  `website_chat_turns` maps 1:1 — `user_message`→query, `route`→category_slug,
  `assistant_message`→response, `created_at`→timestamp (`website_hub/chat_store.py`). Dashboard Hub
  has an equivalent table (confirm its name).
- Ingest a **JSONL export** of that table (schema `{ query, category_slug, response, timestamp, section_id? }`).
  Director's export SQL:
  ```sql
  SELECT user_message AS query, route AS category_slug,
         assistant_message AS response, created_at AS timestamp, id AS section_id
  FROM website_chat_turns
  WHERE assistant_message <> '' ORDER BY created_at ASC;
  ```
- **Bonus ground-truth to use:** `website_chat_faq_entries` = human-approved reusable answers (a real
  correctness signal for FP); `normalized_question` exact-match reuse is the *existing* baseline —
  report how much more ChorusGraph's *semantic* cache catches at FP < 1%.

### 3.2 Temporal-split replay
- **Seed** the cache from the *earlier* slice of traffic (e.g. first 70% by timestamp); **evaluate** on the *later* slice. This mirrors production ("would a later query hit an earlier cached answer") and prevents the trivial seed==eval leak.
- Reuse the H2 `gate()` unchanged. Run over the full later slice (thousands of turns).

### 3.3 Statistical rigor in the report (the part H2 lacked)
- **Minimum-sample gate:** do **not** report a slug/threshold as "FP < budget" unless `n_would_serve ≥ MIN_HITS` (default 300). Otherwise mark `INSUFFICIENT DATA`.
- Report the **upper confidence bound** on FP (Wilson or Clopper-Pearson, 95%), not just the point estimate. Recommend a live threshold **only** where the *upper bound* < 1% with enough samples.
- Output per slug: `h`, `FP_point`, `FP_upper95`, `n_would_serve`, `n_total`, and a verdict: `CACHEABLE` / `INSUFFICIENT DATA` / `UNSAFE`.

### 3.4 Ground-truth for FP on real logs
- A would-serve hit means query Q2 matched the cached answer of an earlier Q1. Q2 has its **own** historical answer A2 in the log. Verdict = compare would-serve(A1) vs actual(A2):
  - **deterministic / `replay_safe` sections** (route, retrieval-set): structural/exact match — measure these fully.
  - **`semantic` (generative) sections:** the answer-vs-answer comparison needs an LLM-judge (deferred, §4). For H3, **exclude them from the FP number but REPORT the coverage gap** — how many potential hits sit in `semantic` sections we cannot yet score. Do not claim savings we can't measure.

## 4. Explicitly OUT of scope
Turning the cache **live** (that's H4, gated on this frontier) · PrismCheckpointer (H4) · the generative LLM-judge for `semantic` FP (its own handoff — flag its urgency based on §3.4 coverage gap) · Postgres ledger normalization · OTel · DSL/engine · Cortex.

## 5. Acceptance criteria
- [ ] Runs over a **real** hub log export with a temporal seed/eval split.
- [ ] Report shows per-slug `h`, `FP_point`, `FP_upper95`, `n_would_serve`, verdict.
- [ ] **Refuses** to recommend a threshold where `n_would_serve < MIN_HITS` (prints `INSUFFICIENT DATA`).
- [ ] Honestly reports the `semantic`-section coverage gap (unmeasured potential hits).
- [ ] Reuses H2 `gate()` unchanged; shadow only, nothing served live.
- [ ] No mocks; `pytest` green; report pasted in handoffback.

## 6. Open questions to answer in handoffback3
1. The real per-slug `(h, FP_upper95)` frontier. Which slugs come back `CACHEABLE` at FP<1%, and at what `h`?
2. How much potential saving sits in `semantic` sections we can't yet score? (→ does the generative-judge handoff become urgent or not?)
3. Recommended production `COARSE`/`VERIFY` thresholds per cacheable slug.
4. Any slug where the frontier says "not worth caching" — cut it.
5. Proposed H4 scope.

## 7. Director dependency (Amin) — the export
Real source: **`website_chat_turns`** in the hub Postgres (Azure Postgres Flexible Server). Steps:
1. Find the server: `az postgres flexible-server list -o table`.
2. Export via the §3.1 SQL to JSONL (psql `\copy`, or `az postgres flexible-server execute`).
3. Hand the JSONL to Cursor; run the replay on Azure if the volume is large.
Do the same for the Dashboard Hub table. No Application Insights / Log Analytics needed — the DB is the
clean source. Until a real export exists, H3 can only dry-run on the H2 proxy (untrustworthy frontier — say so).

## 8. Return format
Same as prior: summary · file tree · how to run · **real** report output (paste the per-slug frontier with confidence bounds) · decisions/deviations · blockers · answers to §6 · design contradictions · proposed H4 scope.

---
*Handoff 3 · architect: Claude · design v0.2 · produce the real (h, FP) frontier with statistical honesty · shadow only.*
