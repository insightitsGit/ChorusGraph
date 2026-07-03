# Cache Profiles — domain-adaptive caching (design addition)

> **Why this exists.** Run `20260703_042206` showed ChorusGraph far ahead of LangGraph in finance and
> flat-to-behind in healthcare. Root cause: caching effectiveness is a property of the **data**, not the
> framework. Our cache assumed *similar question ⇒ same answer* everywhere; finance satisfies that,
> healthcare violates it. The fix is not a "healthcare mode" — it is a small, fixed set of **measured
> attributes** attached per node × category, so any domain becomes a configuration, not a rewrite.
>
> Companion to [`ENGINE_DESIGN_v0.1.md`](ENGINE_DESIGN_v0.1.md) (§5 cache interceptor) and
> `DESIGN_v0.3_PRISM_ENGINE.md` (§4 memory & search tiers).

---

## 1. The four axes (what actually varies across domains)

| Axis | Question it asks | Evidence from our runs |
|---|---|---|
| **Input sensitivity** | Does a small change in the question change the answer? | FX paraphrases ⇒ same rate (smooth). K+ 4.3 vs 5.8 ⇒ opposite clinical advice (brittle). |
| **Temporal volatility** | Does the same question's answer change over time? | FX rates move daily; clinical guidelines change over months. |
| **Context dependence** | Does the answer depend on who is asking? | Finance `memory_seed` profile tasks; patient-specific clinical judgments. |
| **Error cost** | What does a wrong cached answer cost? | Stale FX rate = minor. Wrong drug recommendation = severe. |

These are (near-)independent. One axis cannot represent them: finance is *smooth but volatile*;
healthcare is *brittle but stable*. Two domains are two corners of the space, not the whole space.

## 2. The four domain archetypes (the categories, mapped)

The axes yield four canonical archetypes. **Every domain we can construct lands in one of these —
usually as a mixture across its pipeline hops (see §4).**

| Archetype | Axes signature | Example domains | Cache strategy |
|---|---|---|---|
| **A — Smooth + stable** | low sensitivity · low volatility · low risk | FAQ / customer support, education/tutoring, product docs | Cache **whole answers**, semantic keying, long/no TTL. The *most* cacheable — more than finance. |
| **B — Smooth + volatile** *(finance-like)* | low sensitivity · **high volatility** · low-med risk | FX/market rates, news, inventory/pricing, travel availability | Cache whole answers, semantic keying, **short TTL / freshness window**. Replay-safe inside the window only. |
| **C — Brittle + stable** *(healthcare-like)* | **high sensitivity** · low volatility · high risk | Clinical decision support, legal analysis, code assistance | **Never cache the judgment.** Cache **mid-pipeline facts** (retrieval, guideline summaries, drug-pair severities, API docs) with **fingerprint keying**. |
| **D — Context-bound** | any · any · answer depends on **who asks** | Personalized advisory, memory-backed assistants, account-specific support | Cache only with **scoped keys** (tenant/user/session). A global hit across users is a data leak *and* a wrong answer. |

A domain's archetype is not declared — it is **measured** (§6). And a single product usually spans
archetypes: our healthcare pipeline is C at the writer and A at the retrieval hop.

## 3. The CacheProfile schema

One profile per **category_slug**, overridable per **node**:

```python
class CacheProfile(BaseModel):
    keying:    Literal["semantic", "fingerprint", "exact"]   # ← input sensitivity
    ttl_s:     Optional[int]        # None = no expiry        # ← temporal volatility
    scope:     Literal["global", "tenant", "user", "session"] # ← context dependence
    risk_tier: Literal["low", "high"]                         # ← error cost
    # risk_tier="high" implies: stricter verify threshold, quality-gated seeding (§5),
    # and cache_policy may not exceed EXACT for judgment-producing nodes.
```

- `keying="semantic"` — today's behavior: 64-d coarse → 384-d verify on the raw text.
- `keying="fingerprint"` — key = normalized **structured equivalence key**, not free text. For clinical:
  `{sorted(drugs), topic/condition, binned labs, pipeline_depth}` (the intake artifact already extracts
  this). Semantic asks *"do these sound alike?"*; the fingerprint asks *"is this the same decision?"*
- `keying="exact"` — normalized-string equality only.
- `ttl_s` — entries carry `valid_from`/`valid_until`; the gate treats expired entries as misses. Maps
  naturally onto Cortex's bitemporal model.
- `scope` — the cache key is prefixed by the scope id. `global` = shareable facts; `session` = this
  conversation only. **This is the axis whose misconfiguration caused HC1's 0% hit rate** (cache
  instance siloed per session while repeats arrived across sessions).

## 4. Attachment: node × category, never domain

Domains are mixtures. The healthcare pipeline proves it:

| Hop | Archetype | Profile |
|---|---|---|
| intake (extract facts) | — (cheap, deterministic) | `no_cache` |
| retrieve (guidelines by topic) | **A** | semantic · ttl 30d · **global** · low risk |
| drug_check (pair → severity) | **A** (pure function) | exact/fingerprint · no ttl · global · **should be deterministic, not LLM** |
| analyze / safety (judgment) | **C** | `no_cache` |
| writer (final recommendation) | **C/D** | fingerprint · **session/user scope** · high risk · quality-gated |

Finance for contrast: `fx_rates` = **B** (semantic · ttl minutes-hours · global · low), `user_profile`
= **D** (semantic · no ttl · **user scope**), `compound_*` = **A** (deterministic math — cache or
compute, never LLM).

The engine hook is the existing **node-entry cache interceptor** (`chorusgraph/core/cache_interceptor.py`,
`NodeCacheSpec`) — the profile extends `NodeCacheSpec`; the scheduler consults it before every node.

## 5. Quality-gated seeding (risk_tier="high")

Never seed the cache from a chain that failed its own quality bar. Seed only when ALL hold:
- the chain did not abstain/refuse (no "cannot provide a recommendation" writer outputs),
- grounding/citation requirements met (`grounding_score ≥ groundedness_floor` from `PlanPolicy`),
- for judgment nodes: safety verdict present and approving.

Rationale (measured): HC2 cache replayed its origin outcomes **25/25 faithfully** — including 12
replayed *failures*. A cache amplifies whatever quality you feed it; gating the seeder turns that
amplification strictly positive.

## 6. Profiles are measured, never declared (the profiler)

House rule unchanged: thresholds/attributes come from measurement, not vibes.

- **Sensitivity probe** → sets `keying`. For a category's canonical queries, generate perturbations
  (paraphrase = same meaning; **delta = one changed value/entity**). If paraphrases keep the canonical
  answer and deltas flip it near-invariantly ⇒ smooth ⇒ `semantic`. If deltas that are *semantically
  close* flip the answer ⇒ brittle ⇒ `fingerprint` (and the flipping fields join the fingerprint).
- **Volatility probe** → sets `ttl_s`. Re-ask canonical queries over time; measure answer drift
  half-life.
- **Context probe** → sets `scope`. Same query across profiles/tenants; if answers differ ⇒ scoped.
- Output: a `CacheProfile` per slug, committed with the measurement run id — auditable like the H3
  threshold frontier.

## 7. What this fixes, concretely

| Observed problem (run 20260703_042206) | Axis | Fix via profile |
|---|---|---|
| HC1 healthcare **0% cache hits** (score=None on all 40 rows) | scope | per-session cache silo → `retrieve`/facts become **global**; judgment stays scoped. Hits become possible at all. |
| HC2 success 45% (cache replayed cold failures) | risk_tier | quality-gated seeding blocks failure amplification |
| Clinical near-duplicates unsafe to match on text | keying | fingerprint keying on the intake artifact |
| FX answers replayed across freshness boundary | ttl | short TTL on `fx_rates` |
| Profile payload surfacing for an FX question (task-0004) | scope + keying | user-scoped `user_profile` entries can never match a global `fx_rates` query |

**Latency claim, honest:** archetype-C domains will not see finance-scale whole-answer skips — by
design (safety). Their wins come from mid-pipeline fact caching + deterministic hops + the engine's
concurrent super-step (retrieve ∥ drug_check). Quality rises at the same time because judgments always
run fresh.

---
*Design addition v1 · four measured axes · four archetypes · profiles attach node × category · any new
domain = run the profiler, get the config.*
