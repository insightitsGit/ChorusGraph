# ChorusGraph A/B Benchmark — Methodology (fairness first)

The A vs B benchmark is the moment "better than LangGraph" gets numbers. A rigged or sloppy benchmark
is **worse than none** — it fools us internally and a buyer punctures it in one question. This spec
exists so the result is credible. Companion to [`DESIGN_v0.2.md`](DESIGN_v0.2.md) §15.

## Scope boundary (read before building)
This is a **per-task cost / latency / accuracy** benchmark. It is **NOT** a load / traffic / throughput
test — production-scale concurrency is a *separate* future test. The run (H9) happens on **Azure** for a
true environment. The workload's realism is about **repeat rate** (to exercise the cache), not concurrency.

## The setup
- **Container A** = the finance agent on **LangGraph** (baseline).
- **Container B** = the finance agent on **ChorusGraph** (H4–H7).
- Same domain (finance), same task set, same workload.

## The one rule that makes it credible: ONLY THE FRAMEWORK VARIES
Everything else must be **identical** across A and B:
- Same model (Gemini, same version, same temperature).
- Same tools (Frankfurter FX, `compound_interest`, …) and same tool code.
- Same prompts / system messages.
- Same KB / retrieval corpus / DB.
- Same query workload.

**Container A must be a *competent* LangGraph build — not a strawman.** Use LangGraph's own
checkpointer, standard ReAct/patterns, sensible prompts. If A is hobbled, the benchmark is worthless to
*you* (you'll believe a false number) and dead on arrival to any buyer. A "fair-baseline audit" is a
required deliverable — someone who knows LangGraph signs off that A is a reasonable implementation.

## What legitimately differs (this IS the product)
- **A:** LangGraph state/checkpoint; no semantic cache, no Cortex memory, no route ledger.
- **B:** ChorusGraph cache (measured thresholds), Cortex memory, agent patterns, Route Ledger.

**CacheProfile disclosure (H21):** when B (or C/D/E/F ChorusGraph scenarios) uses semantic cache, the
[`CacheProfile`](../docs/CACHE_PROFILES.md) per `category_slug` must be documented in
[`benchmark/SCENARIOS.md`](../benchmark/SCENARIOS.md) — keying, TTL, scope, risk tier. Measured profiles
come from [`benchmark/profiler.py`](../benchmark/profiler.py) (offline fixtures or live probes).

## Workload design (this is how we escape the H3 data desert)
The H3 finding was: production traffic is too thin to validate the cache. The benchmark *generates* the
volume instead:
- A **realistic finance query set** with realistic **repeat / paraphrase rates** — caching value lives
  entirely in repeats, so the repeat distribution must mirror real usage (some queries recur, some are
  paraphrased, some are novel). Random-unique queries → cache never hits → proves nothing.
- **Controllable volume** — large enough that per-slug hits clear the `MIN_HITS=300` bar from H3, so the
  cache FP/hit numbers are statistically real, not n=2.
- Document the repeat/paraphrase model so the workload's realism can be challenged and defended.

## Measurement schema (IDENTICAL logging in both containers)
Per task: `latency_ms`, `llm_calls`, `tokens_in`, `tokens_out`, `cost_usd`, `task_success`,
`answer` (for accuracy scoring). B-only: `cache_hit`, `cache_score`, `grounding_score`.
Aggregate: P50/P95 latency, total cost, cost-per-task, accuracy rate, cache hit-rate (B), per-slug.

## Anti-rigging checklist (all must hold)
- [ ] Only the framework differs (model/tools/prompts/KB/workload identical).
- [ ] Container A signed off as a competent LangGraph build (fair-baseline audit).
- [ ] B's cache thresholds are **MEASURED** (the shadow/H3 frontier), **never hand-tuned to win**
      (the H4 0.82/0.85 demo thresholds must not appear here).
- [ ] Accuracy scored by a fixed rubric applied identically to A and B.
- [ ] Report discloses where A is weaker and whether that's a fair reflection of the framework.
- [ ] **B reasons comparably to A** — B runs its LLM ReAct/AgentNode path, **not** a regex shortcut A
      lacks. Otherwise the A↔B delta conflates "regex vs LLM" with "cache vs no-cache," and B's win is
      a routing shortcut (which A could also use), not ChorusGraph's cache/memory. The delta must
      isolate the ChorusGraph layer.

## What the benchmark also produces
The A/B run is where the **LATER belief-knob thresholds get calibrated** (§7.5) — `confidence_stop`,
`groundedness_floor` need empirical grounding/confidence distributions, which this run provides. So the
benchmark validates the cache *and* unlocks the belief tier.

## Honest reporting
Report deltas with confidence intervals, not point estimates. State the workload's repeat model. If B
wins on cost but loses on latency (or vice-versa), say so plainly — a mixed, honest result is more
useful and more credible than a clean one nobody believes.

## Containers C–F and product Q&A
This spec covers **A vs B** fairness. Multi-agent rigs (C/D healthcare, E/F finance) and Chorus
**integration patterns** are documented in:

- [`FINANCE_MULTIAGENT_CHORUS.md`](FINANCE_MULTIAGENT_CHORUS.md) — **correct Container F wiring** (reference)
- [`PRODUCT_QA_BENCHMARK.md`](PRODUCT_QA_BENCHMARK.md) — buyer Q&A, container status

Distinguish **library behavior** (proven in B + F) from **benchmark wiring mistakes** (pre-fix F, healthcare D).

## Canonical MVP results (Azure)

Latest regression: **`mid_20260708_111539`** (100 tasks/scenario). See [`benchmark/results/mvp_scenarios/README.md`](../benchmark/results/mvp_scenarios/README.md) and [`benchmark/results/BENCHMARK_LATENCY_LLM_SUMMARY.md`](../benchmark/results/BENCHMARK_LATENCY_LLM_SUMMARY.md).

---
*Methodology only · the benchmark is built in H8, run/analyzed in H9.*
