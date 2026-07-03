# Handoff H21 — CacheProfile: domain-adaptive caching (design addition → implementation)

**Director:** Amin · **Architect:** Claude · **Engineer:** Cursor
**Spec:** [`docs/CACHE_PROFILES.md`](../docs/CACHE_PROFILES.md) — read it FIRST; this handoff implements it.
**Date issued:** 2026-07-03

---

## 0. Why (one paragraph)

Run `20260703_042206`: ChorusGraph beats LangGraph decisively in finance and is flat-to-behind in
healthcare. Verified root cause: our cache assumes *similar question ⇒ same answer* — true in finance
(smooth intents), false in healthcare (K+ 4.3 vs 5.8 ⇒ opposite advice). Additionally HC1 recorded
**0% cache hits with `cache_score=None` on all 40 rows** because `HC1Runner` silos the runtime (and its
cache) per `case.session_id` (`benchmark/hc1/runner.py` `_session_wrapped`) while workload repeats
arrive **across** sessions — an empty cache on every new session. The fix is the **CacheProfile**: four
measured attributes (`keying`, `ttl_s`, `scope`, `risk_tier`) attached per node × category. Domains
become configuration, not code.

**Standing rules:** deterministic-first · Prism-native comms · no mocks (recorded fixtures OK) ·
thresholds/attributes MEASURED, never hand-tuned · benchmark fairness sacred · commit/push only when the
Director asks (trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`).

---

## T1 — CacheProfile schema + profile registry

**Files:** `chorusgraph/sections/models.py` (extend) · new `chorusgraph/sections/profiles.py`

1. Add `CacheProfile` (pydantic) exactly per `CACHE_PROFILES.md` §3:
   `keying: semantic|fingerprint|exact` · `ttl_s: Optional[int]` · `scope: global|tenant|user|session` ·
   `risk_tier: low|high`.
2. Profile registry: `profiles.py` maps `category_slug -> CacheProfile`, loadable from a committed
   config (e.g. `chorusgraph/sections/profiles.default.json`), overridable per node via `NodeCacheSpec`.
3. Defaults per §4 of the spec: `fx_rates`=B (semantic, ttl short, global, low) ·
   `user_profile`=D (semantic, no ttl, **user** scope) · `clinical_guidelines` retrieval=A
   (semantic, ttl 30d, **global**, low) · clinical judgment/writer=C (fingerprint, session scope,
   **high** risk) · `compound_*`= deterministic (no LLM at all).

**Exit:** unit tests — registry resolution (slug default → node override), schema validation.

## T2 — Gate + interceptor honor the profile

**Files:** `chorusgraph/cache_gate/gate.py` · `chorusgraph/cache_gate/sidecar.py` (as needed) ·
`chorusgraph/core/cache_interceptor.py` (`NodeCacheSpec`)

1. **Scope:** cache entry keys are prefixed `scope_id = {global|tenant:X|user:X|session:X}`; the gate
   only matches entries within the caller's scope. A `user_profile` entry can never answer a global
   `fx_rates` query (this is the task-0004 poisoning fix).
2. **TTL:** entries store `valid_from`/`valid_until`; expired ⇒ miss (and eligible for pruning). Align
   the field names with Cortex's bitemporal vocabulary.
3. **Keying:**
   - `semantic` = current two-stage path (unchanged).
   - `exact` = normalized-string equality.
   - `fingerprint` = match on a caller-supplied structured key (see T3), NOT on free text.
4. **risk_tier="high"** ⇒ use the stricter measured verify threshold and enforce quality-gated seeding
   (T4); judgment nodes with high risk may not exceed `EXACT`.
5. Thread the profile through `NodeCacheSpec` so the engine's node-entry interceptor applies all of the
   above per node.

**Exit:** unit tests per axis — scope isolation (seed as user A, query as user B ⇒ miss), ttl expiry
(freeze time via injected clock, no `datetime.now` sprinkled), exact vs semantic vs fingerprint
resolution, high-risk threshold selection.

## T3 — Clinical fingerprint keying

**Files:** new `benchmark/healthcare/fingerprint.py` (or `chorusgraph/transforms/` if generic) ·
`benchmark/hc1/*` · `benchmark/hc2/*`

1. `clinical_fingerprint(intake_artifact, *, pipeline_depth) -> str`: normalized, deterministic key from
   `{sorted(drugs), topic/condition, binned labs (define bins in code, documented), pipeline_depth}`.
   The intake hop already extracts these fields — no new LLM work.
2. HC1/HC2 cache seed + lookup for **judgment-level** entries key on the fingerprint (profile C);
   **retrieval/drug facts** entries key semantically on topic (profile A, global scope).
3. Paraphrase of the same case ⇒ same fingerprint (hit). One changed lab/drug ⇒ different fingerprint
   (miss). Add exactly this pair of tests.

**Exit:** the fingerprint tests above; no free-text semantic matching on clinical judgments anywhere.

## T4 — Quality-gated seeding

**Files:** `benchmark/hc1/cache_helpers.py` · `benchmark/hc2/cache_helpers.py` · shared helper in
`chorusgraph/cache_gate/` (so it's product, not benchmark-only)

Seed ONLY when all hold (spec §5): not abstained/refused (reject writer outputs matching the
"cannot provide a recommendation" family) · grounding requirements met (`grounding_score ≥
groundedness_floor` where available) · for judgment nodes: safety verdict present and approving.
Log a trace event when seeding is refused, with the reason.

**Exit:** test — a failing/refusing chain does NOT seed; a passing chain does. (This blocks the HC2
failure-amplification measured at 12/25 replayed failures.)

## T5 — Fix the HC1 zero-hit (scope bug) — the measurable payoff

**Files:** `benchmark/hc1/runner.py` · `benchmark/hc2/runner.py`

1. Split cache lifetime from session lifetime: ONE `runtime.cache` shared across the whole run for
   **global-scope** entries (facts); session-scoped entries isolated by the T2 scope prefix on the SAME
   shared store — not by separate cache instances per session.
2. Wire HC1's gate + measurement so `cache_score`/`cache_decision` always land on the row (score=None on
   a queried-but-empty cache is acceptable; score=None because fields were dropped is not — assert in test).
3. Offline proof (stub Gemini, recorded fixtures): run the healthcare workload twice through HC1 —
   assert repeats/paraphrases of seeded cases produce `cache_hit=True` with `llm_calls=0` on hit rows,
   and that judgment entries do NOT hit across different fingerprints.

**Exit:** the offline proof test green; HC1 hit rate on a repeat-heavy offline workload > 0 with facts
cached globally and judgments fingerprint-scoped.

## T6 — The profiler (measure, don't declare)

**Files:** new `benchmark/profiler.py` (+ `benchmark/run_profiler.py` CLI)

Per spec §6, for a given category slug: **sensitivity probe** (paraphrase vs one-value-delta
perturbations → recommends `keying`, and which fields belong in the fingerprint) · **volatility probe**
(re-ask over time → recommends `ttl_s`; for offline runs accept recorded time-series fixtures) ·
**context probe** (same query across profiles → recommends `scope`). Output: a `CacheProfile` JSON per
slug + the measurement evidence, committed next to the profile registry with the run id.

**Exit:** profiler runs offline on recorded fixtures for `fx_rates` (recommends B-shape) and
`clinical_guidelines` (recommends C-shape: fingerprint + judgment-no-cache). No fabricated data — real
Gemini or recorded fixtures only.

## T7 — Docs

`docs/CACHE_PROFILES.md` is written (the canonical spec). Additionally: cross-link it from
`docs/DESIGN_v0.3_PRISM_ENGINE.md` §4 (memory & search tiers) and from `docs/BENCHMARK.md` (profiles are
part of "only the framework varies" — the SAME profile config must be disclosed per scenario). Update
`benchmark/SCENARIOS.md` with the per-scenario profile in use.

---

## Order & gates

T1 → T2 → (T3 ∥ T4) → T5 → T6 → T7. Full `python -m pytest tests/ -q` green after each task; the
langgraph grep gate on `chorusgraph/{core,checkpoint,compat,transport}` still holds throughout.

**Non-goals for H21:** re-running the Azure matrix (that waits until the H20 gaps + workload-generator
misalignment fix land — separate handoff), migrating FC1/FC2/HC2 to the core engine (P7).

## Return format (`handoffbackH21.md`)

Per task: files changed · exit-criteria pass/fail with real command output · any deviation from the
spec'd schema (flag, don't improvise) · the HC1 offline hit-rate number from T5 · profiler outputs from
T6 with their evidence files. State anything unverifiable plainly. No commits unless asked.

---
*H21 · implements docs/CACHE_PROFILES.md · four measured axes, four archetypes, profiles per node×category ·
fixes HC1 zero-hit (scope), HC2 failure-amplification (gated seeding), clinical text-matching (fingerprint).*
