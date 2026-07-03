# ChorusGraph — Project Journal

A narrative record of how ChorusGraph was conceived, designed, benchmarked, mis-scoped, corrected, and
re-founded as an engine-first LangGraph replacement. Written to be read cold by anyone joining the effort.

**Roles throughout:** Director = Amin (AI Solution Architect, Insight IT Solutions) · Architect = Claude
(writes specs, verifies returns against *real* code) · Engineer = Cursor (implements). The Director's
standing rules: honest analysis (no cheerleading, no hedging), ground everything in real repo code,
fairness in benchmarking is sacred, no public claims until it's a true LangGraph replacement.

---

## 1. Origin — "why not a LangGraph-similar product?"

The Director already owned a family of products (the **Prism family**) and saw that, together, they could
form an agent runtime to rival LangGraph:

- **PrismLang** — tenant-seeded vector projection; `PrismEnvelope` (turn_id, agent_id, category_slug,
  vector, `rule_chain` audit); ~414 bytes/hop; also ships a native **checkpointer**
  (`AsyncPostgresCheckpointer`, `AsyncJsonFileCheckpointer`) and `BoundaryTranslator`.
- **PrismCache** — semantic cache (RAM/SQLite), `get_or_call`, two-stage gate (64-d coarse recall →
  384-d verify → policy gate: exact / replay_safe / semantic / no_cache).
- **PrismResonance** — wave-interference semantic search (384-d) with a broadcast bus
  (`FrequencyBroadcast` / `InProcessBroadcast` / `RedisBroadcast`) and priority bands.
- **PrismCortex** — bitemporal knowledge graph (`valid_from`/`valid_to`), ACCOMMODATE-on-correction,
  content-addressed determinism, `digest`/`recall`/`explain`/`conflicts`/`sleep`, native 128-d.
- **CHORUS** — machine-to-machine tensor transport (179 ms transatlantic, ~4.45× bandwidth).
- **PrismAPI** (`prismlib-plus`, open-source, `C:\code\PrismLabPlusAPI`) — vector-native API layer:
  *providers embed once, agents retrieve pre-projected float32 vectors over CHORUS — no re-embedding.*

The thesis: LangGraph gives you an execution graph but nothing else; ChorusGraph could give you the graph
**plus** built-in semantic cache, memory, vector transport, and observability — cheaper, faster, more accurate.

Naming: candidates included ChorusAgentic; the Director chose **ChorusGraph**.

---

## 2. The design phase (DESIGN_v0.2)

Grounded design work produced `docs/DESIGN_v0.2.md` and companions (WORKFLOW, BENCHMARK, PROCESS,
ENTERPRISE_READINESS). Key threads:

- **The "4 gaps"** vs LangGraph: graph/DSL surface, execution engine, tool calling, and
  HITL + checkpointing + streaming.
- **Execution patterns** (Director's push): not just ReAct — also Reflection, Plan-and-Solve, agent loop.
  Implemented as `chorusgraph/agents/` (`run_react`, `run_reflection`, `run_plan_solve`, `run_agent_loop`).
- **Role-typed nodes** (`chorusgraph/nodes/roles.py`): `RoleTemplate`, `Node.with_role`,
  Researcher/Writer/Validator, `promote`.
- **Cache correctness** (§8) and the **belief tier** (§7.5 `PlanPolicy`: `confidence_stop`,
  `groundedness_floor`).
- **PrismCortex** introduced to resolve knowledge conflicts by taxonomy + time (bitemporal) — the
  Director specified this to fix a real ingestion bug.

The Director repeatedly enforced **deterministic-first**: *"even a 5-year-old knows we should not have
multiple LLM calls."* Function/deterministic paths before any LLM generation.

The handoff loop (`docs/PROCESS.md`) ran H1–H13 + E1–E9, each with a `handoffH*`/`handoffbackH*` pair.

---

## 3. The benchmark saga (fairness is sacred)

`docs/BENCHMARK.md` codified the one rule: **only the framework varies** — same model (Gemini), tools,
prompts, KB, workload. Baseline must be *competent*, not a strawman. Thresholds **measured**, never tuned.

Containers:
- **A** = finance agent on LangGraph (baseline). **B** = finance agent on ChorusGraph.
- **C** = healthcare multi-agent baseline. **D** = healthcare multi-agent on ChorusGraph.
- **E/F** = finance multi-agent.

Bugs found and fixed by verifying against **raw JSONL**, not summaries:
- **H8 "82% vs 27%" was fake** — Container A never actually called tools (`tool_calls=0` on all 47 FX
  tasks). Fixed in H11 (A now 44/47 tool calls; accuracy tied ≈84%). A broken baseline is worse than none.
- **Cortex silently downgraded 128→64** in H12; confirmed real and fixed in H13 (native 128-d).
- **Architect's own over-read** — claimed "D generates 58% more output tokens" from a single case;
  aggregates showed D output ≈ C (lower at depth 4). Owned and retracted — the exact small-sample error
  the Architect had been criticizing.

Blocker throughout: **Gemini 10k/day quota** repeatedly throttled volume runs.

---

## 4. The multi-agent D investigation

Multi-agent D (healthcare) was *worse* than single-agent, which made no sense. Root cause, confirmed
against code: envelopes were **write-only** — produced each hop, never read/consumed — and every hop
called Gemini. No LLM was ever skipped, so D could only be ≤ C. The only lever that cuts wall-time is
**skipping LLM calls** (cache), not bounding input tokens.

The fix landed as a proper **cache gate node** mirroring B/F: `vector_ingress` → `cache_gate` (two-stage
`gate()`, measured thresholds) → on hit, `route_after_cache_d` jumps straight to the writer (skipping all
agents) and the writer returns the cached response with **0 LLM calls**. Better than the per-hop helper
the Architect had proposed.

**But the Architect's verification caught that the fix was unproven:** the only run on record showed
**0 cache hits across 10 cases** — every case ran the full pipeline. Not bad luck: the runner builds a
**separate cache per `session_id|depth`**, and no repeated question in the workload shared the same
(session, depth), so a hit was structurally impossible. Recommended fix: a **global** semantic cache
across all D cases (like B), scheduled into the re-benchmark (P7 of the engine handoff).

---

## 5. The critical realization — it was NOT a complete replacement

The Director asked: *"why isn't this a complete replacement of LangGraph?"* Verification against the
`chorusgraph` library gave the blunt answer: **it was built on top of LangGraph, not instead of it.**

| Capability | Who owned it |
|---|---|
| Graph DSL + compiler | LangGraph (`langgraph.graph.StateGraph`) |
| Execution engine (scheduler) | LangGraph |
| Checkpointing | LangGraph (`chorusgraph/checkpoint/prism.py` wrapped `SqliteSaver`/`PostgresSaver`) |
| HITL, streaming, tools | LangGraph |
| Route Ledger | ChorusGraph (`adapter/wrap.py` = a *"non-invasive LangGraph adapter"*) |

Remove LangGraph → nothing ran. The design had let "adapter-first / LangGraph-compatible" quietly
substitute for the Director's actual requirement: **replacement**. The Architect owned this as its miss —
the one job was to flag that "compatible ≠ replacement" at the first `import langgraph`, and it hadn't.

The Director was (rightly) frustrated: *"I asked for a complete replacement from the beginning."*

---

## 6. The recovery — engine-first, and the mess is smaller than it looked

Honest damage triage:
- **Wasted:** time optimizing and benchmarking a *layer* — those A/B and C/D numbers compare
  "LangGraph vs LangGraph+Prism" and are void as *replacement* evidence.
- **Not wasted (most of it):** every Prism-native component is real and correct; the benchmark harness
  and fairness discipline are reusable; the domain understanding carries forward.

The decisive finding: **ChorusGraph was missing exactly one component — the scheduler.** Everything else
LangGraph provides already existed Prism-native and was merely wired to LangGraph:

- Message = `PrismEnvelope` · Bus = Resonance broadcast · Search = `ResonanceEngine`
- Checkpointer = `prismlang.AsyncPostgresCheckpointer` (has `aget_delta_channel_history` → time-travel)
- Transport = CHORUS (`prism.cluster.transport`) · Federation = PrismAPI (`prism.api`)
- Memory = Cortex · Cache = `cache_gate` · Trace = Route Ledger · Roles + patterns = already built

Guardrail installed as the actual compensation: **`grep -rn langgraph chorusgraph/core` == 0 becomes a
CI gate**, every handoff must name the LangGraph debt it deletes, and no "replacement" claim ships on
layer-benchmark numbers.

---

## 7. The Director's communication mandate

The Director sharpened the architecture with a hard constraint: **all communication in the engine is
Prism-native.**
- Node-to-node messages = **PrismLang envelopes** on the **Resonance bus**, routed by Resonance search.
- Cross-machine = **CHORUS**.
- **Cross-container multi-agent = PrismAPI** (`prism.api`), with `prism.bridge.vector` /
  `BoundaryTranslator` re-projecting envelopes at the boundary — carrying the pre-projected vector so a
  cross-container hop does **zero re-embedding** (the embed-once mandate, enforced across containers).

Role agents and the multi-agent patterns are first-class citizens on that bus, not afterthoughts.

---

## 8. The deliverables produced

- **`docs/ENGINE_DESIGN_v0.1.md`** — engine-first architecture. Three layers (authoring DSL / Prism
  services / execution engine) over one communication fabric (envelope + Resonance + CHORUS + PrismAPI).
  The only net-new component is the L1 super-step scheduler.
- **`handoffs/handoffCORE_MVP.md`** — the complete, self-contained Cursor handoff. Encodes every standing
  rule (MVP-first *and* complete; deterministic-first; Prism-native comms; no mocks; fairness; the CI
  gate). Phases P1–P4 = the **complete MVP** (single runtime, fully working, zero LangGraph); P5
  (distribution), P6 (federation), P7 (migration shim + honest re-benchmark + D cache fix) scheduled in
  the same doc. Includes a dated schedule, milestone gates, the LangGraph-deletion debt table, test
  requirements, definition of done, and the return format.

PrismAPI/CHORUS confirmed open-source and local (`prismlib-plus` v0.7.0, `C:\code\PrismLabPlusAPI`,
import root `prism`) — P6 is grounded in real modules, not a placeholder.

---

## 9. Lessons banked

1. **"Compatible" is the opposite of "replacement."** The first `import langgraph` in the core was the
   moment to stop; a goal without a guardrail drifts.
2. **Verify against raw data, not summaries.** Every fake win (H8) and every real bug (Cortex 128→64,
   D cache-siloing) surfaced from reading JSONL/code directly.
3. **Own over-reads fast.** The Architect's "58% more tokens" and the retracted per-hop fix were caught
   and owned rather than defended.
4. **Wall-time only drops when you skip the LLM.** Bounding input tokens or bounding handoffs does not;
   caching does.
5. **Most of the "engine" already existed.** The recovery was a rewire, not a rewrite — because the Prism
   family had every part except the scheduler.

---

## 10. Open items / next actions

- Confirm the P1 start date (schedule anchors on 2026-07-07; MVP ≈ Aug 05).
- Check for **overlap** between `prismlib-plus` (`prism.cache`, cluster mesh, observability) and
  `chorusgraph` (`cache_gate`, ledger) so caching/observability has a single owner before build.
- Re-run A/B + C/D benchmarks **on the engine** (P7), fix the D global-cache siloing, report deltas with
  confidence intervals.
- Bring the `prismlib-plus` editable install into the ChorusGraph dev environment.

---
*Journal maintained by the Architect. Update it at each milestone gate (G1…G-DONE).*
