# ChorusGraph

**A LangGraph-compatible agent runtime with semantic cache, taxonomy RAG, auditable memory, and CHORUS-native transport built in — not bolted on.**

Status: **Design phase.** No runtime code yet. See [`docs/DESIGN_v0.2.md`](docs/DESIGN_v0.2.md) for the ground-truthed product design.

---

## What it is

LangGraph answers *how do I wire nodes*. ChorusGraph answers *how do I run agents without paying the integration tax* — the semantic cache, vector DB, reranker, checkpoint, and cross-service transport come as one runtime keyed by a single tenant vector substrate, instead of duct tape you assemble yourself.

It composes the existing Prism family as first-class primitives:

| Layer | Component | Role |
|-------|-----------|------|
| L0 — hop | PrismLang | Per-hop state compression (64-d) + `rule_chain` audit |
| L1 — cache | PrismCache | Semantic `get_or_call`, Resonance-scored |
| L2 — knowledge | PrismRAG | Mapping-first Graph RAG + taxonomy slugs |
| rerank | PrismResonance | Wave-interference retrieval |
| L3 — memory | PrismCortex | Deterministic, bitemporal, byte-identical replay |
| transport | CHORUS Fabric | Cross-region tensor spine (179 ms transatlantic, 4.45× bandwidth) |
| federation | PrismAPI | Cross-tenant `remote` nodes |

## The four gaps it fills

The Prism family is strong in the engine room and empty at the developer-facing top. ChorusGraph builds the four missing layers: **(a)** graph/DSL surface, **(b)** execution engine/scheduler, **(c)** tool calling, **(d)** human-in-the-loop + durable checkpointing + streaming.

## Guiding principles

- **Adapter-first.** Run existing LangGraph `StateGraph`s with Prism checkpoint + cache before building a native engine. Prove value, then earn the engine.
- **Safe cache before fast cache.** The skip-the-LLM decision uses a two-stage gate (coarse 64-d recall → full-precision verify); generative outputs are never replayed verbatim. See `DESIGN_v0.2.md` §8.
- **Measure, don't assert.** Cost/latency targets are experiments (hit rate `h`, overhead `o`, per-slug false-positive budget), not marketing numbers.

## Provenance

Productizes integration already dogfooded in production in `InsightitsAIAgent/meeting-scheduler/` (Website Hub, Dashboard Hub).

---

*Insight IT Solutions · design only · no implementation committed.*
