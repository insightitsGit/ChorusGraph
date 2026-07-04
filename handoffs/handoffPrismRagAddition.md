# Handoff PrismRagAddition — real L2 retrieval (PrismRAG) + depth-aware fingerprint interim fix

**Director:** Amin · **Architect:** Claude · **Engineer:** Cursor
**Refs:** [`docs/DESIGN_v0.3_PRISM_ENGINE.md`](../docs/DESIGN_v0.3_PRISM_ENGINE.md) §4.3 (L2 — PrismRAG + Resonance rerank, always the design's plan, never wired) ·
[`docs/CACHE_PROFILES.md`](../docs/CACHE_PROFILES.md) · [`chorusgraph/nodes/retrieve.py`](../chorusgraph/nodes/retrieve.py) (the existing hook) ·
Library: `C:\code\PrismRagLib` (package `prismrag-patch`, `PrismRAGPatch` + adapters for Chroma/pgvector/Pinecone/Weaviate)
**Date issued:** 2026-07-03

---

## 0. Why (grounded in the verified run)

Run `20260703_215802` (40×8, seed 42, post-CacheProfile-fix): finance is a clean sweep, HC1 healthcare-
single is a real win, but **HC2 healthcare-multi still trails LangGraph 52.5% vs 70%**, concentrated at
**depth-6 cache hits (4/10 success vs depth-4's 10/13)**. Root cause chain, verified in code:

1. `benchmark/healthcare/tools.py::retrieve_guidelines` — its own docstring says **"stand-in for
   pgvector KB"**: keyword-token-overlap scoring over **21 hardcoded snippets**, no real vector search,
   no taxonomy separation. This is the L2 retrieval layer the design always specified as
   "PrismRAG + pgvector" (§4.3) — never actually built.
2. `chorusgraph/nodes/retrieve.py::make_retrieve_handler` / `resonance_rerank` exist but **HC2's
   `retrieve_node` bypasses them entirely** — it calls `retrieve_guidelines` directly, so even the
   Resonance rerank we already have isn't exercised there.
3. Consequence: retrieval can't discriminate clinical nuance beyond topic bucket, so the CacheProfile
   fingerprint (drugs + topic + labs + depth) is the only thing separating "same decision" from
   "different decision" — and at depth-6 it isn't discriminating finely enough.

Two fixes, sequenced fast-then-deep:

- **Part A (fast, days):** make the fingerprint depth-aware NOW, using only what already exists —
  unblocks HC2 without waiting on new infrastructure.
- **Part B (the real fix, the reason for this handoff):** replace the "stand-in" with **real PrismRAG
  retrieval** — a real vector-indexed KB + `PrismRAGPatch` taxonomy remap — and use its category-aware
  vectors as a **principled fingerprint substrate**, not hand-picked fields.

**Standing rules unchanged:** deterministic-first · Prism-native comms (envelope, never raw dict) ·
no mocks/fakes (recorded fixtures OK; a real Chroma/pgvector instance for integration tests, not a
fake one) · thresholds/attributes MEASURED not declared · benchmark fairness sacred (retrieval upgrade
applies to ChorusGraph scenarios only — LangGraph baseline keeps its own tool-based retrieval,
unchanged, so the comparison still isolates the framework) · commit/push only when the Director asks
(trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`) · full `python -m pytest tests/ -q`
green after every task · langgraph grep gate holds.

---

## PART A — Interim fix: depth-aware fingerprint (do this first, ships in days)

### T1 — Widen the clinical fingerprint by pipeline depth
**Files:** `benchmark/healthcare/fingerprint.py` · `benchmark/hc1/*` · `benchmark/hc2/*` ·
`tests/test_clinical_fingerprint.py`

Today `pipeline_depth` is one field among several in `clinical_fingerprint(...)`. Problem: at higher
depth, more clinical nuance is in play (more hops' worth of facts feed the judgment), so a fingerprint
built from the same field SET regardless of depth is too coarse once depth rises — two depth-6 cases
that match on drugs+topic+labs can still need different judgments because of what deeper hops add
(interactions, safety context).

**Fix:** make the fingerprint's field SET grow with depth, not just carry depth as a value:
- depth ≤ 2: `{drugs, topic, binned_labs}` (current behavior, unchanged — don't regress HC1/depth-2/4).
- depth ≥ 4: add `{cited_ids_signature}` (sorted set of guideline IDs actually cited by `retrieve`,
  from `hop_artifacts["retrieve"]["cited_ids"]` — already computed, zero new cost).
- depth ≥ 6: additionally require `{interaction_severity_signature}` (sorted severities from
  `drug_check`, already computed).

Document the bands as named constants, not magic numbers. A case whose deeper-hop facts differ now
produces a different fingerprint at that depth, so it correctly misses instead of replaying a
insufficiently-specific match.

**Exit test:** two depth-6 cases with identical drugs/topic/labs but different `cited_ids` (simulate by
constructing hop_artifacts directly) MUST produce different fingerprints. Two depth-2 cases identical
on the depth-2 field set MUST still match (no regression). Rerun the offline HC1/HC2 two-pass proof
(existing `test_hc1_cache_scope.py` pattern) and record the new depth-6 hit-quality number.

**This alone should meaningfully close the depth-6 gap — ship and measure before starting Part B.**

---

## PART B — Real L2 retrieval: wire PrismRAG (the actual fix, replaces the stand-in)

### T2 — Stand up a real vector-indexed KB (Chroma for local/CI; pgvector optional for parity with prod)
**Files:** new `benchmark/healthcare/kb_vector.py` · `benchmark/healthcare/GUIDELINES` (expand corpus)

1. Expand `GUIDELINES` beyond 21 snippets if you have more real guideline text available (more corpus
   = more meaningful test of retrieval quality); if not, 21 is fine to start — the point is real vector
   search over what exists, not corpus size, for this task.
2. Embed each guideline chunk once (reuse the existing embedder — `chorusgraph/embedders.py` — do NOT
   introduce a second embedding model; embed-once discipline applies here too) and load into a local
   **ChromaDB** collection (`chromadb.Client()` in-process — no external service needed for tests/CI).
   Real `pgvector` is the production target per the original design citation, but Chroma is the
   honest, dependency-light choice for this handoff's tests; note in the return if a real pgvector
   instance is available to also verify against.

**Exit:** unit test — chunks inserted, a query returns nearest-neighbor results, deterministic given
the same embedder (no LLM call in this hop).

### T3 — Wire `PrismRAGPatch` for taxonomy-aware remap
**Files:** new `benchmark/healthcare/prismrag_mapping.py` · `benchmark/healthcare/kb_vector.py`

1. Build a `Mapping` for the clinical corpus: categories = the existing `topic` values
   (`hypertension`, `diabetes`, `anticoagulation`, `safety`, `lipids`, ...), rules = keyword→category
   (start from terms already in `GUIDELINES[*]["text"]` — e.g. "hyperkalemia"→`hypertension`/
   `heart_failure` overlap categories, "bleeding"→`anticoagulation`). Document the rule list; it should
   be inspectable and extensible, not buried.
2. Instantiate `PrismRAGPatch(license_key=..., mapping=..., alpha=0.25, adapter="chroma")` — license
   key from an env var (`PRISMRAG_LICENSE_KEY`); **tests that need a live license skip cleanly if unset,
   never fake a license response.** If `prismrag_patch.mapping.Mapping` supports a lower-level
   deterministic remap test path without hitting the license server, prefer that for CI (check the
   real `license.py`/`mapping.py` source before assuming — flag what you find).
3. Wrap the Chroma collection with `ChromaAdapter(patch, collection)`; use `.add()` on ingest and
   `.query()` at retrieval time instead of the raw `retrieve_guidelines()` keyword scorer.

**Exit:** deterministic remap test (same text+vector+mapping → same output, no randomness/LLM, per the
library's own contract) · a query for an ambiguous term (e.g. "monitoring" — appears in multiple
topics) returns better category separation with the patch than without (compare same query, patch on
vs off, on the same corpus).

### T4 — Replace the retrieve node's stand-in with the real pipeline
**Files:** `benchmark/hc2/nodes.py` (`retrieve_node`) · `benchmark/hc1/*` (mirror) ·
`chorusgraph/nodes/retrieve.py` (reuse, don't duplicate — this is what `make_retrieve_handler` /
`resonance_rerank` were built for)

1. Route HC1/HC2's `retrieve_node` through `chorusgraph.nodes.retrieve.make_retrieve_handler`, with
   `retrieve_fn` = the T2/T3 Chroma+PrismRAG pipeline (topic, query) → chunks, instead of calling
   `retrieve_guidelines` directly. This finally exercises `resonance_rerank` in the real path too — a
   second, already-built Prism asset gets used for real.
2. `cited_ids` on the artifact now come from real retrieval results (chunk ids), not a keyword-scorer
   fallback.
3. **Fairness:** LangGraph baselines (HL1/HL2) keep their own existing retrieval tool, completely
   unchanged — only the framework varies. State this explicitly in `benchmark/SCENARIOS.md`.

**Exit:** HC1/HC2 offline tests (stub LLM) pass with the new retrieval path; `cited_ids` populated from
real query results; no LLM calls added (retrieval stays deterministic, per the embed-once/
deterministic-first rule).

### T5 — Fold PrismRAG's category signal into the CacheProfile fingerprint (the elegant part)
**Files:** `benchmark/healthcare/fingerprint.py` · `docs/CACHE_PROFILES.md` (update)

Replace/extend Part A's hand-picked `cited_ids_signature` with the **remapped category assignment**
from `PrismRAGPatch.mapping.assign_category(...)` (or the retrieved chunks' category slugs) as a
fingerprint component. Rationale: two cases whose queries resolve to the same taxonomy category after
remap are the same clinical decision family; two that resolve differently aren't — this is a
*measured* signal (deterministic given the mapping) rather than a hand-tuned field list. Keep Part A's
depth-banded field growth as the scaffold; swap the retrieval-derived fields for the sharper
PrismRAG-based ones once T4 lands.

**Exit:** the T1 negative test (different retrieved evidence ⇒ different fingerprint) re-verified using
the real category signal instead of the simulated `cited_ids`; document the final fingerprint
definition in `CACHE_PROFILES.md` §4 (update the healthcare row).

### T6 — Re-measure
**Files:** `benchmark/run_scenarios.py` invocation only — no new code

Re-run the same fixed comparison (seed 42, 40 tasks, repeat band 40%) for HC1/HC2 only (finance and
HL/HC-single are untouched by this handoff — no need to re-run them). Report the new HC2 depth-6
hit-quality number against this handoff's baseline (52.5% overall, 4/10 at depth-6-hit). State the
delta plainly — if it doesn't close the gap fully, say so; this is a real measurement, not a target to
hit by construction.

---

## Order & effort

T1 (interim fix) ships and gets measured **before** T2 starts — don't let Part B block Part A's quick
win. T1: 1–2 d. T2: 1–2 d. T3: 2 d (license/mapping wiring + determinism proof). T4: 1–2 d. T5: 1 d.
T6: re-run + report, no dev time.

## Return format (`handoffbackPrismRagAddition.md`)

Per task: files · exit criteria pass/fail with real command output · **actual `PrismRAGPatch`/`Mapping`
signatures verified vs assumed** (flag any deviation) · whether a live license was available or tests
skipped cleanly without one · the T1 interim measurement AND the T6 final measurement, both reported ·
anything blocked, stated plainly. No commits unless the Director asks.

---
*PrismRagAddition · Part A ships a fast, scoped fix using only existing code · Part B replaces the
healthcare KB's explicitly-labeled "stand-in" with real PrismRAG retrieval and folds its taxonomy
signal into the cache fingerprint · fairness preserved — only ChorusGraph scenarios change.*
