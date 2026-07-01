# ChorusGraph — Product Design v0.2 (Ground-Truthed)

**Status:** Draft · design only · no implementation committed
**Supersedes:** v0.1 draft. This version is verified against the actual repos; every
"exists today" claim is code-cited, and v0.1's optimistic or inaccurate claims are corrected.
**Author intent:** A unified agent runtime that fills LangGraph's integration gaps using the
existing Prism family as first-class, built-in primitives — cheaper on tokens, faster on
cross-region hops, stronger on accuracy and auditability.
**Audience:** Product, architecture, and engineering leads at Insight IT Solutions.

---

## 0. What changed from v0.1 (read this first)

v0.1 was a strong shape and most of it holds. This version was written after reading the
repos. Corrections that matter:

| # | v0.1 claim | Ground truth (code-cited) | Consequence |
|---|-----------|---------------------------|-------------|
| 1 | 64-d JL substrate powers routing, retrieval, and cache | The **cache hit/miss decision itself runs in 64-d**: `PrismCache.get_or_call` does `embed(query)`→384-d, then `projector.project()`→**64-d**, then match if `constructive_score ≥ threshold` (`prism/cache/cache.py:335-353`) | The "skip the LLM call" decision is made in coarse 64-d space. This is the primary correctness risk and needs its own design (§8). |
| 2 | Adapter "replaces checkpointer with PrismCheckpointer" | **No checkpointer exists today** — `website_hub/graph.py:132` compiles with bare `graph.compile()`. No persistence, no `interrupt`, no resume anywhere in the hubs | Checkpointing, human-in-the-loop, and durable resume are **greenfield builds**, not adaptations. Scope accordingly. |
| 3 | Cache threshold 0.92 | Lib default is `0.92` (`prism/cache/cache.py:127`), but the **dashboard hub overrides to 0.88** (`dashboard_hub/prism_cache_service.py:43`) | Real operating point is looser than stated → more hits, higher false-positive exposure. |
| 4 | Grounding guard protects replayed answers | `hallucination_guard.py` validates **citation IDs** against available KB chunks and strips invalid ones — it does **not** check semantic faithfulness of the answer to the query | A replayed *generative* answer is **not** made safe by the existing guard. §8 adds the missing check. |
| 5 | CHORUS makes the runtime faster | CHORUS p50 is **179 ms transatlantic**, 4.45× **bandwidth** reduction, 1.8×–4.5× latency vs baselines (`CHORUS/README.md:55`, `info.md:37`). In-process hops use the PrismLang envelope, **not** CHORUS | CHORUS's win is **cross-region / cross-service**, not single-process. Positioning must say so or a reviewer will puncture it. |

Everything else in v0.1 — the section model, taxonomy-guarded cache key, adapter-first
strategy, and hub-to-product mapping — is sound and carried forward.

---

## 1. Executive summary

LangGraph gives you a graph of nodes, edges, and (optionally) checkpoints. Everything
else — semantic cache, taxonomy RAG, resonance rerank, auditable memory, tensor transport,
federated retrieval — is left to the integrator. Insight IT has **already built that
integration by hand** in two production graphs (Website Hub, Dashboard Hub), wiring
`@prism_node`, `PrismCache`, `PrismResonance`, PrismAPI, and a taxonomy KB onto a LangGraph
`StateGraph`.

**ChorusGraph** productizes that hand-wiring into a single runtime contract, so an
external developer gets it from one install instead of copying `website_hub/graph.py`.

**Core thesis (corrected):** one shared, tenant-seeded 64-d vector substrate powers routing,
transport, and *cache candidate recall* — while a **full-precision re-check gates any decision
that skips real work**. Similar situations reuse work at every layer; the coarse projection
finds candidates, and a precise check prevents wrong reuse.

**The product IS the four gaps.** From the earlier architecture map, the Prism family is strong
in the engine room (memory, state, retrieval, transport) and empty at the top (developer-facing
orchestration). The four missing layers are: **(a)** a graph/DSL surface, **(b)** an execution
engine/scheduler, **(c)** tool calling, **(d)** human-in-the-loop + durable checkpointing +
streaming. Building these on top of the existing strengths is the whole product.

**Not in this phase:** runtime code, forking LangGraph, or shipping packages. This defines shape.

---

## 2. What exists today (verified inventory)

This is the honest asset base. "Product" work is what sits on top of it.

| Component | Repo / path | What it actually does (verified) | Role in Orchestrator |
|-----------|-------------|----------------------------------|----------------------|
| **PrismLang** | `PrismLang/` (PyPI `prismlang`) | Per-hop state compression to 64-num vectors (~414 B/turn), tenant-seeded JL projection (`config.DEFAULT_K=64`, `spherical_blend(α=0.3)`), `rule_chain` audit, `@prism_node` decorator, `BoundaryTranslator` | **L0 hop layer + audit + the projector** |
| **PrismCache** | `PrismLabPlusAPI/prism/cache/`, `prism/cluster/cache.py` | Semantic LLM/output cache; `get_or_call` embeds→projects to 64-d→`constructive_score` match; `ClusterCache` for cluster sync | **L1 semantic cache** |
| **PrismResonance** | `PrismResonate/` (PyPI `prismresonance`) | Wave-interference retrieval (`z=A·e^{iφ}`), Phase Coherence Shield drops low-resonance chunks, 384-d, no torch. Supplies `constructive_score` to the cache | **Rerank + cache scoring** |
| **PrismRAG** | `InsightMappingRag/prismrag/` | Mapping-first Graph RAG; taxonomy `category_slug` on chunks; pgvector | **L2 knowledge + taxonomy** |
| **PrismCortex** | `PrismCortex/` (PyPI `prismcortex`) | Deterministic, bitemporal, byte-identical replay memory; digest/consolidate(`sleep`)/recall; content-addressed recall cache (99.6% hit in memory benchmark); corrections retain audit | **L3 agent memory** |
| **CHORUS Fabric** | `CHORUS/chorus_fabric/` | gRPC tensor transport; 179 ms transatlantic p50, 4.45× bandwidth, 0 ms cipher overhead, watermarking | **Cross-region/service spine** |
| **PrismAPI** | `PrismLabPlusAPI/prism/api/`, `website_hub/prismapi_retrieval.py` | Federated retrieval across tenants/networks over CHORUS frames | **`remote` node** |
| **ChorusMesh** | `ChorusMesh/` | Commercial ops layer (licensing, alerts, multi-region) on the same protocol | **Enterprise ops (optional)** |
| **Reference graphs** | `meeting-scheduler/website_hub/`, `dashboard_hub/` | LangGraph `StateGraph` + all of the above, hand-wired, in production | **Dogfood + migration targets** |

**Gaps confirmed absent today:** native graph DSL, a Prism-owned execution engine, a
first-class tool-calling primitive, checkpointing, human-in-the-loop/interrupts, and streaming.

---

## 3. Problem statement

| Pain (LangGraph-centric stacks) | ChorusGraph response | Status of the piece |
|--------------------------------|------------------------------|---------------------|
| State is opaque JSON in a checkpointer | Sectioned state with vector taxonomy | New (schema is design work) |
| Every node re-serializes history as text | PrismLang compresses in-proc; CHORUS for remote hops | **Exists** (PrismLang, hubs) |
| RAG is a separate pipeline | PrismRAG remap + PrismResonance rerank in the retrieve node | **Exists** (hub `rag.py`) |
| LLM cache is a separate product | PrismCache on LLM + eligible node outputs | **Exists** (dogfooded) |
| Long-term memory is DIY | PrismCortex tier with audit/replay | **Exists** (opt-in) |
| Remote agents = custom HTTP | PrismAPI nodes as federated subgraphs | **Exists** (loopback) |
| No durable resume / human approval | Checkpointer + interrupt | **Missing — new build** |
| No standard tool primitive | `tool` node | **Missing — new build** |
| Ops (failover, alerts) = DIY K8s | ChorusMesh | **Exists** (commercial) |

The product gap is a **single runtime contract** external developers adopt without copying
`website_hub/graph.py`.

---

## 4. Architecture big picture (two spines, not one)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       ChorusGraph (runtime)                         │
│   Graph compiler · Scheduler · Checkpoint coordinator · Policy engine       │
│   Built-in nodes: compute · retrieve · cache_gate · llm · tool · remote     │
└──────────────────────────────────────────────────────────────────────────┘
        │            │            │            │            │
        ▼            ▼            ▼            ▼            ▼
   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
   │PrismLang│ │PrismCache│ │PrismRAG│  │Resonance│ │Cortex  │
   │L0 + proj│ │L1 (64-d) │ │L2 tax. │  │rerank  │  │L3 mem  │
   └────────┘  └────────┘  └────────┘  └────────┘  └────────┘

   IN-PROCESS spine  ── PrismLang PrismEnvelope on state (same Python process)
   CROSS-REGION spine ── CHORUS Fabric gRPC  ◄──► PrismAPI  (remote tenant/network)
```

Two transport spines, chosen per edge by the scheduler:
- **In-process** → PrismLang envelope. Cheap; no CHORUS.
- **Cross-service / cross-region** → CHORUS Fabric (this is where the 179 ms / 4.45× win lives).

The controller LLM (Gemini/GPT/Claude) is unchanged and customer-owned.

> **Note on Cortex placement:** the diagram groups Cortex with the processing tiers for brevity, but
> architecturally it is a **data-layer service** (its own server + store), not an inline tier — see §13.

---

## 5. The core engine (the primary gap-fill)

This is the layer the Prism family does not yet have. It has four parts.

**5.1 Graph compiler.** Accepts either a native `Graph` (§10) or an existing LangGraph
`StateGraph`, and lowers it to an internal IR: nodes, edges, section schema, per-section cache
policy, per-edge transport mode. Emits a LangGraph-compatible graph for portability.

**5.2 Scheduler.** Walks the IR in super-steps (the same execution model LangGraph uses). Per
step it: (i) resolves ready nodes, (ii) runs a `cache_gate` before expensive children, (iii)
projects every written section through `PrismProjector` once, (iv) selects the edge transport
mode from the deployment manifest, (v) runs branches in parallel where the graph allows.

**5.3 Checkpoint coordinator.** Persists **section snapshots + graph position** to Postgres.
Stores references to cached section hashes instead of duplicating JSON each step. This is what
enables durable resume, crash recovery, and human-in-the-loop interrupts — none of which exist
today.

**5.4 Policy engine.** One place that owns cache thresholds, per-section cache policy, transport
modes, memory-tier wiring, and grounding hooks — configured in a manifest (§10.2) rather than
hand-coded per graph.

**Honest sequencing note.** Building a *native* engine means re-implementing LangGraph's
Pregel loop. That is the highest-risk, lowest-immediate-value item. **Recommendation:** MVP runs
on LangGraph's own engine via the adapter (§8/§11) and injects Prism through pre/post hooks;
the native engine is Phase 4+. The user's instinct — "fill the core engine" — is the eventual
differentiator (native `cache_gate` in the loop, transport-aware edges), but doing it *first*
inverts the risk curve. Prove the cache/memory value on the adapter before building the engine.

---

## 6. Memory and cache tiers (unified, with real dimensions)

| Tier | Product | Operates on | Orchestrator role | Scope |
|------|---------|-------------|-------------------|-------|
| **L0 — Hop** | PrismLang | 64-d projected vector | Compress state delta between adjacent in-proc nodes | Single run |
| **L1 — Semantic** | PrismCache | embed 384-d → **project 64-d** → match | `get_or_call` on LLM + eligible node outputs, keyed by `(tenant, node_id, section_vector, model)` | Configurable; ClusterCache sync |
| **L2 — Knowledge** | PrismRAG + pgvector | 384-d + taxonomy slug | Retrieve KB chunks; slug on each chunk and state section | Org KB |
| **L3 — Agent** | PrismCortex *(data-layer service — §13)* | knowledge graph + content-addressed cache | Cross-session memory (facts, not chunks); bitemporal audit; byte-identical replay; **auto-fed by default** | User/customer |

### 6.1 State sections (carried from v0.1 — sound)

State is not one blob. A declarative schema splits it into sections, each with `section_id`,
`category_slug` (PrismRAG taxonomy), `content`, `vector` (64-d, computed once per update), and
`cache_policy` (`no_cache | semantic | exact | replay_safe`). Note the added `replay_safe` policy —
see §8. Sections give partial reuse, taxonomy routing, and fewer LLM calls. This productizes what
the hubs already do informally (`route`, `kb_context`, `live_context`, `hub_state`).

### 6.2 Storage model — what actually lives where (verified against code)

Different tiers persist in **different** places. Do not conflate them (an earlier draft wrongly put
the L1 cache on Postgres — it is not).

| Tier | Backing store (real, from `prism/cache/store.py`) | Notes |
|------|----------------------------------------------------|-------|
| **L1 — PrismCache** | **RAM** (`InMemoryStore`, default) or a **SQLite file** (`SQLiteStore`, responses stored as JSON) — *not* Postgres, *not* Redis | Response cache. Multi-server: **per-node, not shared** by default; cross-node needs `ClusterCache` |
| **L2 — Knowledge (PrismRAG)** | **Postgres / pgvector** (via PrismDriver) | The org KB |
| **L3 — Cortex** | Content-addressed cache (JSON) + its own store | Deterministic recall + bitemporal audit |
| **Checkpoint / state** | **Postgres** (section snapshots + graph position) | Net-new build |

Honest infra line: **PrismCache needs no separate cache service (it's RAM/SQLite); Postgres is for
the KB and the checkpointer.** Inside PrismCache the similarity match is PrismLang's `PrismProjector`
(384→64) scored by an in-process PrismResonance wave cache — PrismRAG only contributes the taxonomy
slug on the key, it does not do the projection.

---

## 7. Graph execution model

### 7.1 Built-in node kinds

| Node | Behavior | Prism components |
|------|----------|------------------|
| **compute** | `(state) -> partial state` | Optional `@prism_node` → PrismLang envelope |
| **retrieve** | Query → KB context | PrismRAG remap + pgvector + PrismResonance rerank |
| **cache_gate** | Check L1 before expensive child | PrismCache 64-d recall → **full-precision re-check (§8)** |
| **llm** | Call controller model | PrismCache `get_or_call` + grounding hook |
| **tool** | Side effect (ticket, note) | **New primitive** (productize hub executors) |
| **remote** | Subgraph on another host/tenant | PrismAPI → CHORUS frame |
| **router** | Conditional edge | Deterministic taxonomy/vector rules first, LLM fallback |

### 7.2 Edge transport modes

| Mode | When | Protocol |
|------|------|----------|
| `inproc` | Same process | PrismLang `PrismEnvelope` |
| `chorus_local` | Same cluster, different service | CHORUS Fabric gRPC |
| `chorus_federated` | Different tenant/network | PrismAPI over CHORUS |

Scheduler picks the mode from the manifest — the developer never wires HTTP.

### 7.3 Checkpointing vs caching (distinct concerns)

| Concern | Mechanism |
|---------|-----------|
| Durability / resume / HITL | Checkpoint store (Postgres): section snapshots + graph position — **new** |
| Performance | PrismCache L1 semantic recall — **exists** |
| Compliance replay | PrismCortex bitemporal log — **exists** |

### 7.4 End-to-end turn (see `docs/WORKFLOW.md`)

One turn: project state → route (taxonomy-first) → **cache_gate**. A *verified* hit takes the fast
path and **skips retrieve + LLM** (the cost win); a miss runs retrieve → optional Cortex recall →
llm → grounding. Cache-write and Cortex auto-digest happen **after** the response (async, zero added
latency, §13.3). The Route Ledger logs every step. Full flow + step table in
[`docs/WORKFLOW.md`](WORKFLOW.md).

### 7.5 Planning (ReAct / CoT) — belief-driven, not blind

Planning is **not a separate box**. In a graph runtime the graph *is* the plan:
- **CoT** lives inside the `llm` node (a prompting choice, not a component).
- **ReAct** is a **cyclic subgraph**: `llm`/agent (reason) ↔ `tool` (act), with `router` deciding
  act-or-finish. A prebuilt `agent` node (ReAct / supervisor / swarm) is a **roadmap primitive**
  (§22), not yet first-class. Today's hubs use deterministic routing, not ReAct.

**Stance: deterministic-first, ReAct as fallback.** Structured routing where the intent is known
(cacheable, auditable, cheap); a ReAct loop only when the task genuinely needs dynamic multi-step
reasoning.

**The differentiator — belief-driven control.** LangGraph loops blind (until the LLM says "final"
or `max_iterations`); the developer has no per-step quality signal. ChorusGraph *does* have per-step
signals (grounding_score, cache/constructive_score, Cortex confidence/freshness, rule_chain), so it
exposes a **`PlanPolicy`** that steers the loop by measured belief:

| Param | Effect | Signal (ChorusGraph-only) |
|-------|--------|---------------------------|
| `max_steps`, `token_budget`, `cost_budget` | Hard stop on effort/spend | budgets (table stakes) |
| `confidence_stop` | Finish when confidence ≥ θ | grounding_score / composite |
| `groundedness_floor` | Refuse a final answer below a grounding floor → gather more or abstain | grounding guard |
| `novelty_adaptive_steps` | More steps when novel, fewer near a cache hit | Resonance constructive_score |
| `memory_confidence_gate` | Let a Cortex fact drive the plan only above a confidence/freshness bar | Cortex confidence/freshness |
| `escalation_policy` | Confidence stays low after K steps → escalate (bigger model / HITL / abstain) | confidence trajectory |

**Planning report (Route Ledger):** per-plan telemetry LangGraph can't give — steps taken, budget
spent, the *confidence trajectory* (did each step improve grounding?), final grounding, in-plan
cache-hit-rate, and whether it escalated/abstained. Observable planning, not a black box.

**Honest caveat:** belief-driven control is only as good as the signals. Today `grounding_score` is
citation-validity, not full faithfulness (§8), and confidence may be miscalibrated — so
`groundedness_floor`/`confidence_stop` are **conservative guards, not guarantees** until the scores
are calibrated. Ship budgets + the planning report first; gate the confidence-driven knobs on
calibrated signals.

**Scope:** roadmap, not MVP — the `agent` node + `PlanPolicy` land after the cache/checkpoint spine.

### 7.6 Execution patterns (ReAct · Reflection · Plan-and-Solve)

For a *full* LangGraph replacement these three are table stakes. Coverage:

| Pattern | Status | Built from | ChorusGraph edge |
|---------|--------|-----------|------------------|
| **ReAct** (Thought→Action→Observation) | Composable, not built | `llm` ↔ `tool`, `router` = act/finish (cycle) | Every step logged; PlanPolicy budgets/abstain |
| **Reflection / Self-correct** (generator→evaluator→fix) | Partially native | generator `llm` → evaluator (`llm` critique **or** `tool` running tests) → edge back | The **grounding guard is already a built-in evaluator** (§8) |
| **Plan-and-Solve** (static plan, then execute) | Composable | `planner` `llm` emits a task list → loop runs step N→N+1 | A plan is a deterministic sequence → cacheable + auditable; clean version rides the native scheduler (§5) |

**Build one substrate, not three engines.** All three are the same looping machinery over
`llm` + `tool` + `router`, differing only in stop/route logic. Build the **`tool` node** (net-new,
foundational) + a **generic agent-loop node** + **`PlanPolicy`** (§7.5) once, then ship ReAct /
Reflection / Plan-Solve as **prebuilt configurations**.

**Differentiator (uniform across all three):** each pattern ships *better* than LangGraph's —
**observable** (every step in the Route Ledger), **belief-controlled** (abstain below a grounding
floor), **cache-accelerated** (memoized sub-steps). Parity + a real edge.

**Build order / prerequisite:** `tool` node → generic agent-loop → the three prebuilts → PlanPolicy
knobs (gated on calibrated signals). The `tool` node is foundational and today is only a name in §7.1.

**First-release scope:** DIRECTOR DECISION PENDING — full-replacement goal implies these ship in the
first release; that expands scope well beyond the cache/checkpoint spine (see roadmap).

### 7.7 Role-typed nodes (the multi-agent building block)

One base `Node`; specialized **role variants** (`ResearcherNode`, `WriterNode`, `ValidatorNode`, …)
selected by their signature — the C#-*overloading* intuition (one concept, typed variants). Python
has no compile-time overloading, so the equivalent is a **role-parameterized factory**
(`node(role="researcher", …)`) plus typed convenience constructors. A role variant is *a Node + a
role template*: system prompt, allowed tools, output schema, default execution pattern (§7.6), and
default `PlanPolicy` (§7.5).

- **Convertible / degrades gracefully:** every role variant IS-A `Node` (substitutable anywhere a
  Node goes); a plain `Node` is promotable to a role by attaching a template. Plain Node → "you have
  what you have"; promote it → a powered-up specialist. (Same principle as §11.)
- **This is the multi-agent layer:** a supervisor orchestrates role variants (researcher → writer →
  validator); Reflection (§7.6) *is* a `WriterNode` ↔ `ValidatorNode` loop.
- **Design lean:** composition (Node + attachable role template), not deep inheritance — keeps
  "everything is still a Node" true.
- **Scope:** lands with the `tool` node in H4 — roles are cheap once the tool node + agent-loop exist.

### 7.8 The unified `Agent` type (patterns + properties as config)

The three execution patterns (§7.6) are one machinery differing only in reason + stop strategy, and an
agent is a role-typed Node (§7.7). Unify: **one `Agent` type**, pattern selected by config, on the shared
`run_agent_loop`. An `Agent` IS-A `Node` (`AgentNode`) — drops into a graph like any node; a plain Node is
promotable. Patterns are **pluggable strategies** (reason_fn + route_fn + defaults), not an if-else monolith.

```
Agent(pattern="react"|"reflection"|"plan_solve", tools, model, role,
      policy=PlanPolicy(...), pattern_opts={...})
```

**Shared (PlanPolicy):** `max_steps`, `token_budget`, `cost_budget`, `on_exhaust`
(best_effort | abstain | escalate), `trace_level`.

**Per-pattern — NOW (active, ship with defaults; mostly anti-failure guards):**

| Pattern | Knobs |
|---------|-------|
| ReAct | `max_tool_calls`, `require_tool_before_finish`, `stop_on_repeated_action`, `observation_char_limit` |
| Reflection | `max_revisions`, `critic_model`, `evaluator` (llm_critique \| run_tests \| grounding_guard), `stop_when_no_improvement` |
| Plan-Solve | `max_plan_steps`, `replan_on_failure`, `on_step_failure` (retry \| skip \| abort \| replan), `checkpoint_after_step`, `validate_plan` |

**Belief tier — LATER (interface defined NOW, behavior disabled until A/B-calibrated, §7.5):**
`confidence_stop`, `groundedness_floor`, `memory_confidence_gate`, `escalation_policy`,
`novelty_adaptive_steps`. These are the LangGraph-can't-copy differentiator — they steer on
grounding/confidence numbers that must be A/B-calibrated first. **Ship the API surface now** (stable,
visible, documented as "requires calibration"); **enable the behavior after the A/B.**

**Design lean:** small curated set + good defaults (zero-config works). NOW knobs = anti-failure guards
(no thrash, no answer-without-a-tool, no spin) + debuggability (`trace_level`).

---

## 8. Semantic cache correctness (the make-or-break section)

The entire cost/latency thesis depends on the cache being right when it says "skip." Today the
skip decision is made in **64-d** at `constructive_score ≥ 0.88–0.92`. That is fine for finding
*candidates*; it is not sufficient to *authorize skipping real work*. Two failure modes:

1. **Within-category near-neighbors.** The taxonomy slug blocks `platform_products` from
   colliding with `meetings`, but two different questions inside the *same* slug can sit above
   threshold in 64-d and return the wrong cached answer.
2. **Generative replay.** Reusing a cached *draft reply* for a "similar situation" can emit a
   fluent, wrong answer. The existing `hallucination_guard.py` only validates citation IDs — it
   will not catch a semantically wrong-but-well-cited replay.

### 8.1 Design: two-stage gate + policy by output type

**Stage 1 — coarse recall (existing):** 64-d `constructive_score` retrieves top-k candidates.
**Stage 2 — full-precision verify (new):** re-score the top candidate on the **384-d** embedding
(and/or exact-token check) before authorizing reuse. Only a candidate passing both stages is a hit.

Then gate by what is being reused:

| `cache_policy` | Example section | On a verified hit |
|----------------|-----------------|-------------------|
| `exact` | deterministic tool result, formatted price | Reuse directly |
| `replay_safe` | retrieval set, routing decision | Reuse; cheap re-validate against fresh KB |
| `semantic` | LLM draft answer | **Never reuse verbatim** — reuse as *grounding context* for a cheaper/shorter LLM pass, then run the grounding guard |
| `no_cache` | live tool output, PII | Always recompute |

The rule that makes this safe: **generative outputs are never replayed without re-validation
against fresh retrieval.** The cache saves the *expensive retrieval + reasoning setup*, not the
final generative commitment, unless the output is provably deterministic.

### 8.2 The false-positive budget, made measurable

Define `FP_rate = P(verified hit is wrong)`. v0.1 asserted `< 1%` with no mechanism. Here it is a
*measured* quantity per slug: shadow-run the cache (serve live, log what it *would* have returned),
diff against ground truth, and only raise a slug's policy from `no_cache`→`semantic` once its
shadow FP_rate is under budget. This turns the riskiest number into an earned, per-slug rollout.

---

## 9. The four gaps, filled

**(a) Graph / DSL surface** — `prism.orchestrator.Graph` with a declarative section schema
(§10). Also ingests LangGraph `StateGraph`. This is the developer-facing layer that does not
exist today.

**(b) Execution engine / scheduler** — §5. Adapter-first (runs on LangGraph's engine), native
engine later.

**(c) Tool calling** — a first-class `tool` node with a typed signature, retry/timeout policy,
and side-effect isolation. Today this is an internal hub convention (`try_deterministic_tools`,
executors); the product needs it as a contract external developers can rely on.

**(d) Human-in-the-loop + durability + streaming** — the checkpoint coordinator (§5.3) enables
`interrupt`/resume; the scheduler emits a token/state/event stream over the same in-proc or CHORUS
channel. All three are absent today and are net-new.

---

## 10. Developer experience (design sketch — not implemented)

### 10.1 Minimal graph
```python
# DESIGN SKETCH ONLY — not shipped
from prism.orchestrator import Graph, SectionSchema, CachePolicy
from prism.orchestrator.nodes import retrieve, llm, cache_gate

schema = SectionSchema({
    "message":    {"category": "user_input",       "cache": CachePolicy.NONE},
    "kb_context": {"category": "knowledge",         "cache": CachePolicy.REPLAY_SAFE},
    "response":   {"category": "assistant_output",  "cache": CachePolicy.SEMANTIC},  # never verbatim
})

g = Graph("support-agent", tenant_id="acme", sections=schema)
g.add_node("retrieve", retrieve(source="pgvector", top_k=6, rerank="prismresonance"))
g.add_node("draft",    llm(model="gemini-2.5-flash", cache=True, grounding=True))
g.add_edge("retrieve", "draft")
g.compile(checkpointer="prism-postgres")   # enables resume + HITL
```

### 10.2 Manifest (ops)
```yaml
# DESIGN SKETCH ONLY
tenant_id: acme
graph_id: support-agent
cache:
  coarse_threshold: 0.88        # 64-d recall
  verify_threshold: 0.95        # 384-d full-precision gate (§8.1)
  cluster_sync: true
transport:
  default: inproc
  remote_providers:
    - {id: insightits-legal-kb, mode: chorus_federated}
memory:
  cortex: {enabled: true, scope: customer_id}
```

### 10.3 Install
```bash
pip install "prismlib-plus[orchestrator,enterprise,cache,fabric]"
```

---

## 11. LangGraph compatibility (adapter-first)

- **Phase A — Adapter (MVP):** accept compiled `StateGraph`; add `PrismCheckpointer` (new,
  section-aware); wrap nodes via `@prism_node`; inject retrieve/cache/router as pre/post hooks
  from the manifest — no graph rewrite. Website Hub + Dashboard Hub become reference graphs.
- **Phase B — Native DSL:** `prism.orchestrator.Graph`; still exports LangGraph JSON.
- **Phase C — CHORUS-native distributed graph:** partition across services; CHORUS edges;
  ChorusMesh for ops.

**Principle:** any Orchestrator graph exports to LangGraph JSON; Prism-specific nodes degrade to
plain Python callables with warnings. You never trap the customer.

---

## 12. Federated agents (PrismAPI as a node)

`[router] → [remote:insightits-legal-kb] → [llm]`. Provider exposes `PrismAPIProvider`
(`semantic_fields`, `id_field`); consumer declares a `remote` node with `provider_id` and a query
template from a state section; the response lands in `kb_context` with the provider's
`category_slug`. Same pattern as `warm_prismapi_loopback()`, productized. **Open security item:**
cross-network federated retrieval needs an explicit authn/authz + tenant-isolation story (§17).

---

## 13. Where Cortex earns its place (cost, speed, accuracy)

Your hint says Cortex "overall saves cost, improves speed, and adds accuracy." Grounded read:

- **Accuracy:** byte-identical replay + bitemporal audit means a recalled fact is the *same* fact,
  with a defensible "what did the agent know on date X" answer. That is a real accuracy/governance
  gain L1 caching cannot provide.
- **Cost/speed:** Cortex's *own* content-addressed recall cache showed 99.6% hit in a
  memory-recall benchmark (30 Gemini calls / 2,563 recalls). **Caveat, stated honestly:** that is
  a *repeated-recall* workload, not diverse agent turns — do not extrapolate 99.6% to end-to-end
  graph savings. Cortex helps most where the same facts are recalled many times (support, CRM,
  long-lived customer context).
- **Placement:** Cortex is the `replay_safe`/`exact` backstop behind the L1 semantic cache — the
  tier you trust to *skip* work because its answers are deterministic and audited.

### 13.1 Cortex is a data-layer service, not an inline tier

Unlike PrismLang/PrismCache/PrismRAG/Resonance (which act *during* a turn), Cortex is a **stateful
backing memory service** that persists and serves across sessions. It ships its own `server.py` and
store, so it deploys **beside the database** and scales independently. It serves **facts with
provenance rendered from a bitemporal graph — not raw chunks.** Raw-chunk retrieval is PrismRAG (L2).
Keep the line clean: *PrismRAG = "find relevant chunks"; Cortex = "recall a known fact and prove it."*

### 13.2 Two roles (same `digest`/`recall` API)

1. **Reference / tool** — an agent node calls `recall()` mid-turn to look something up. Memory as an
   explicit tool in the agent's reasoning.
2. **Long-term controller memory** — the runtime auto-`digest()`s each turn and feeds relevant
   recalls back to the controller across sessions. Ambient memory it doesn't have to ask for.

### 13.3 Automatic memory policy (decided)

Role ② is **automatic by default** — safe only under three constraints, because the real cost is
extra LLM calls and context tokens, *not* CPU:

- **Async digest, never inline.** The response ships first; digest runs out-of-band (background
  worker / Cortex's STAGED→`sleep()` path). Automatic memory adds **zero latency** to the turn.
- **Salience-gated writes.** Cortex `Band`s skip `NEUTRAL`/`ARCHIVE` turns and fast-track only
  corrections/important facts — so we don't pay an extraction LLM call on trivial turns.
- **Budgeted, relevance-filtered recall.** Inject top-k facts under a token budget, not the whole
  memory. Recall is mostly a content-addressed cache hit (~99.6% in benchmark) — cheap.

**Tunable + opt-out per graph.** Automatic is the default; a graph can raise/lower the salience
threshold, change the token budget, or turn Cortex off entirely. CPU is a non-issue relative to LLM
cost — and because Cortex runs as its own service, its CPU is isolated from the runtime and scales
independently.

**Honest caveat — correctness, not cost:** automatic injection means memory quality affects *every*
answer; a wrong/stale fact poisons the controller by default. This is safe *because* recall is
content-addressed + bitemporal and flags `provisional`/`confidence` — automatic is a bet on Cortex's
trustworthiness, which the code supports.

### 13.4 Storage: Postgres now, multi-DB in Phase 2

Cortex must be **built-in and ready to sit on the DB/server layer as its own layer.** Today its
backing store targets **Postgres only**. **Phase 2:** connectors for other databases (other
SQL / vector / graph stores) so a customer can point Cortex at their existing datastore. Until then,
Postgres is a hard dependency for L3. Tracked in the roadmap (§16).

---

## 14. Reference mapping — current hubs → product (verified)

| Today | Orchestrator primitive |
|-------|------------------------|
| `StateGraph` + routers (`website_hub/graph.py`, `routers.py`) | Graph + router node |
| `WebsiteHubState` / `DashboardHubState` | Section schema |
| `classify_intent` / `route_after_rag` | Router + taxonomy |
| `rag_retrieve` + `assess_retrieval` | retrieve + cache_gate |
| `gemini_master` + `validate_grounding` + `hallucination_guard` | llm + grounding hook (§8) |
| `prism_audit` / `BoundaryTranslator` | Built-in audit export |
| `get_prism_cache()` / `prism_cache_service` | L1 cluster-aware cache |
| `warm_prismapi_loopback()` / `prismapi_retrieval` | remote node |
| `try_deterministic_tools` | Deterministic fast-path (before LLM) |
| pgvector `kb_chunks` | L2 knowledge store |

Website Hub = public RAG/education reference. Dashboard Hub = authenticated tools + live context.

---

## 15. MVP scope (v0.1 release)

**In scope:**
1. `PrismCheckpointer` — section snapshots on Postgres (net-new).
2. `cache_gate` with **two-stage gate (§8.1)** + LLM `get_or_call` wrapper.
3. LangGraph adapter — run existing compiled graphs with Prism checkpoint + cache.
4. `retrieve` node — PrismRAG + PrismResonance + pgvector (single tenant).
5. Audit — `BoundaryTranslator` report per turn.
6. Shadow-mode cache FP measurement (§8.2) on one ported reference graph.
7. **Route Ledger** — durable per-turn log of every node entered, edge taken, and the router's
   `rule_chain` (the *why*), plus cache hit/miss + score and grounding score. Cheap: the signal
   already exists in `rule_chain` + `with_pipeline_trace`; the work is persisting it and making it
   queryable. This is the "observability without a LangSmith subscription" deliverable (§22).

**Out of scope v0.1:** visual editor; native CHORUS partition scheduler; Cortex auto-wiring
(manual opt-in only); multi-provider fan-out; ChorusMesh billing inside the runtime; native
execution engine.

**Success metrics — with a model behind them (replacing v0.1's asserted numbers):**

Let `h` = verified L1 hit rate on the master LLM node, `c` = per-call LLM cost, `L` = per-call LLM
latency, `o` = cache lookup overhead (384-embed + 64-project + resonance scan).

- **LLM-call cost:** savings ≈ `h`. Target −30% ⇒ requires **h ≈ 0.30 at FP_rate < budget**.
  *Unknown until measured on Dashboard Hub traffic — that measurement is metric #1, not an assumption.*
- **P50 latency:** Δ ≈ `h·L − o`. Improvement only if `h·L > o`. Publish `h`, `L`, `o` from the
  ported graph; do not claim −20% before they're measured.
- **Cache false-positive rate:** per-slug shadow FP_rate < budget (e.g. 1%) *before* that slug is
  allowed to serve from cache.
- **Adapter compatibility:** Website + Dashboard graphs run unmodified.

---

## 16. Roadmap (product phases, not dates)

| Phase | Deliverable | Customer value |
|-------|-------------|----------------|
| 0 — Design | This doc + ADRs | Alignment |
| 1 — Adapter + safe cache | LangGraph + two-stage PrismCache + section checkpoint + Route Ledger | Drop-in cost savings, provable safety, full route audit |
| 2 — Retrieve primitive | Taxonomy RAG + Resonance node | Better answers, less bleed |
| 3 — HITL + streaming | Checkpoint interrupts, token stream | Enterprise workflows |
| 4 — Remote node | PrismAPI federation | Cross-network agents |
| 5 — Native DSL + engine | `prism.orchestrator.Graph`, native scheduler | Ergonomics + CHORUS-native distribution |
| **2 (hardening)** — Security | Cache-poisoning controls, tool sandboxing, mTLS default, cipher audit, federated authn/authz | Regulated/enterprise trust (§21) |
| **2 (hardening)** — Cortex + multi-DB | Automatic long-term memory (async, salience-gated); connectors beyond Postgres | Durable audited memory on any datastore (§13.3–§13.4) |

---

## 17. Risks and open questions

| Risk | Severity | Mitigation |
|------|----------|------------|
| 64-d cache false positives | **High** | Two-stage gate (§8.1); per-slug shadow FP budget (§8.2); never replay generative output verbatim |
| Building native engine too early | High | Adapter-first; defer engine to Phase 5 |
| LangGraph API churn | Medium | Adapter boundary; pin versions; export portable JSON |
| HITL/checkpoint is net-new, underestimated | Medium | Scope it as a real build, not an adaptation |
| Federated retrieval security (cross-tenant over CHORUS) | Medium-High | Explicit authn/authz + per-tenant projection isolation before Phase 4 |
| CHORUS positioned as general speed | Medium | Position as cross-region/bandwidth win, with the 179 ms/4.45× numbers scoped correctly |
| Overlap with PrismMemory/PrismCortex framing | Medium | One story: Cortex = L3; Orchestrator = the runtime that wires L0–L3 |
| Cache poisoning (shared cache serves a bad entry widely) | High | Per-tenant cache isolation, write-authorization, provenance signing, never-cache untrusted sections (§21) |
| Unaudited homegrown CHORUS cipher | Medium-High | Default mTLS/TLS; cipher opt-in; independent crypto audit before any security claim (§21) |
| Tool execution → injection side effects | Medium-High | Allowlists, capability scoping, sandboxing, HITL approval for high-risk tools (§21) |
| PrismCache silent `HashEmbedder` fallback (non-semantic) if `sentence-transformers` missing | **High** | Pin a real embedder; **fail loudly** on fallback; never run on HashEmbedder in prod |
| L1 cache not shared across servers by default (per-node RAM/SQLite) | Medium | Use `ClusterCache` for cross-node; document that response storage stays per-node |
| Automatic Cortex memory injects a wrong/stale fact into the controller | Medium-High | Content-addressed + bitemporal recall; `provisional`/`confidence` flags; async + salience-gated; per-graph opt-out (§13.3) |
| Cortex backing store is Postgres-only today | Low-Medium | Multi-DB connectors in Phase 2 (§13.4); until then Postgres is a hard L3 dependency |

**Open questions for review:**
1. **Name:** ChorusGraph vs PrismGraph vs bundle under PrismLang brand?
2. **Open core:** adapter free in `prismlib` vs orchestrator only in `prismlib-plus`?
3. **LangGraph relationship:** partner ("enhance LangGraph") or competitor narrative publicly?
4. **First vertical:** sell runtime standalone or only with Vertical AI Web Agents?
5. **Section schema type:** **DECIDED — hybrid.** Pydantic for the `Section` schema (validation +
   serialization + cache-key safety, applied at boundaries); TypedDict for the LangGraph graph
   `State` (native, keeps the hot path fast). Pydantic v2 is fast and Cortex already uses it.
6. **Verify threshold:** what 384-d re-check score and per-slug FP budget are acceptable to ship?

---

## 18. Competitive frame (broader than LangGraph)

LangGraph is the orchestration comparison, but the "cache + memory + retrieval runtime" claim also
competes with: **LangGraph + LangMem**, **LlamaIndex Workflows**, **GPTCache / Redis semantic
cache** (on L1), and **Temporal** (on durable execution / HITL). The defensible wedge is the
*combination keyed by one tenant vector substrate* — semantic cache, taxonomy retrieval, auditable
replay, and CHORUS transport in one runtime — not any single layer, each of which has a point
competitor. Say this plainly in any external review; it is stronger than "we beat LangGraph."

---

## 19. One-paragraph narrative

LangGraph answers *how do I wire nodes*. ChorusGraph answers *how do I run agents without
paying the integration tax* — semantic cache at every hop (with a full-precision safety gate),
taxonomy-aware retrieval, auditable deterministic memory, and CHORUS transport for cross-region
hops, all keyed by one tenant vector substrate. Teams keep their LLM; they replace the duct tape
between cache, vector DB, reranker, checkpoint, and microservices — and they get a per-slug proof
that the cache is safe before it ever skips a call.

---

## 20. Next design artifacts (still no code)

1. **ADR-001:** Section schema spec (fields, cache keys, taxonomy binding, `replay_safe` semantics).
2. **ADR-002:** Two-stage cache gate + shadow FP measurement protocol.
3. **ADR-003:** LangGraph adapter boundaries (patch vs wrap) + PrismCheckpointer ER diagram.
4. **Sequence diagram:** one Dashboard Hub turn through Orchestrator layers, cache hit and miss paths.
5. **Pricing sketch:** Orchestrator in ChorusMesh tiers vs standalone OSS adapter.

---

## 21. Phase 2 — Security Hardening (register)

Security is a lane where ChorusGraph is genuinely strong (self-hosted sovereignty, per-tenant
isolation, auditable replay) — but **full control = full responsibility**: you own the whole attack
surface. This register tracks every known issue so none "flies." Status: **Have** / **Partial** / **Open**.

| # | Issue | Status | Plan |
|---|-------|--------|------|
| 1 | Cache poisoning — one bad entry served to many users | Partial | §8 two-stage gate + taxonomy guard; add per-tenant cache isolation, write-authorization, entry provenance/signing, never-cache for user-generated sections |
| 2 | Homegrown CHORUS cipher | **Open** | Default to mTLS/TLS; keep cipher-as-matmul as opt-in perf mode; **independent crypto audit before any security claim** |
| 3 | Federated PrismAPI authn/authz (Tenant A ↔ Tenant B) | Partial | Per-tenant projection isolation exists; add mutual auth, server-side per-request authorization, cross-tenant query audit + rate limits |
| 4 | Tool execution safety (injection → side effects) | **Open** | Allowlists, capability scoping, sandboxing, HITL approval for high-risk tools |
| 5 | Prompt injection via retrieved/tool content | Partial | Grounding guard helps; add instruction/data separation, provenance tagging, egress controls |
| 6 | Multi-tenant vector isolation | Have (verify) | `tenant_id` in cache key + per-tenant projection seed exist; verify enforced across cache, RAG, *and* transport |
| 7 | Sensitive data (PII) in Route Ledger / traces | Partial | Self-hosted helps; add PII redaction, access control, retention policy |
| 8 | Secrets management (LLM keys, DB creds) | Have | `prismcortex_key_vault.py`; enforce no-secrets-in-state/logs |

**Ship gates:** items **#2 (unaudited crypto)** and **#4 (tool safety)** must not ship *as security
features* until closed. #1 is the security face of the §8 cache-correctness work and rides with it.
Everything else is incremental hardening. Strengths to lead with in sales: #6, #8, and (once
closed) #3 — sovereignty + isolation + audit beats "send your traces to a SaaS."

---

## 22. Interoperability & integration strategy (build to standards, not adapters)

LangChain's hundreds of integrations are its historical moat — but that moat is **shrinking**,
because the ecosystem is standardizing around two things LangChain predates:

- **LLM API convergence** — most providers now expose OpenAI-compatible endpoints. ChorusGraph
  needs **one normalized LLM interface** handling the residual differences (tool-calling format,
  streaming, structured output, token/cost accounting) across the major providers — not one wrapper
  per vendor.
- **MCP (Model Context Protocol)** — the emerging standard for tools/data sources. A **native MCP
  client is a first-class ChorusGraph primitive**: it inherits the entire MCP ecosystem (files,
  GitHub, Slack, databases, and growing) with zero per-integration code.

**Net integration surface:** ~a dozen well-chosen adapters — one LLM interface, one MCP client, a
handful of vector/embedding/DB adapters — **not 500**. The messy long tail (legacy/proprietary
sources not yet on MCP) is inherited **for free** via the LangGraph adapter (§11): a customer runs
LangChain's loaders/tools inside nodes on the ChorusGraph engine.

**Position:** don't out-breadth LangChain — stand on the standards it predates. Being a late
entrant is the advantage here, not the handicap.

---

*Document version: 0.2 draft · ground-truthed against repos · design only · no implementation committed.*
