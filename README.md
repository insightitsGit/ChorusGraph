# ChorusGraph

**Native agent runtime with semantic cache, taxonomy RAG, auditable memory, and CHORUS transport — Prism-family orchestration without the integration tax.**

> **Terminology:** **ChorusGraph** = native engine (`chorusgraph.core`) + full product stack. **Not LangGraph.** See [`docs/TERMINOLOGY.md`](docs/TERMINOLOGY.md) and [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md).

Status: **v1.0.0 enterprise release** — native engine, four swappable plug-in ports, CI-hardened. See [`docs/INSTALL.md`](docs/INSTALL.md) · [`docs/WHITEPAPER.md`](docs/WHITEPAPER.md).

---

## Install

```bash
pip install chorusgraph                              # core
pip install "chorusgraph[retrieval]"                 # + PrismRAG vector plug-in
pip install "chorusgraph[dev,gemini,retrieval]"      # full dev tier
```

Quick start, optional extras, and **PrismRAG implementation guide**: [`docs/INSTALL.md`](docs/INSTALL.md)  
Plug-in ports (cache, memory, tools, retrieval): [`docs/PLUGINS.md`](docs/PLUGINS.md)

```python
from chorusgraph import Graph, START, END, ChorusStack

stack = ChorusStack.defaults(tenant_id="demo")
# stack = stack.with_retrieval(my_prismrag_backend)  # see INSTALL.md
```

---

## What it is

LangGraph answers *how do I wire nodes*. ChorusGraph answers *how do I run agents without paying the integration tax* — the semantic cache, vector DB, reranker, checkpoint, and cross-service transport come as one runtime keyed by a single tenant vector substrate, instead of duct tape you assemble yourself.

It composes the existing Prism family as first-class primitives:

| Layer | Component | Role |
|-------|-----------|------|
| L0 — hop | PrismLang | Per-hop state compression (64-d) + `rule_chain` audit |
| L1 — cache | PrismCache | Semantic `get_or_call`, Resonance-scored |
| L2 — knowledge | PrismRAG plug-in | Swappable `RetrievalBackend` — keyword default, vector + taxonomy opt-in |
| rerank | PrismResonance | Wave-interference retrieval |
| L3 — memory | PrismCortex | Deterministic, bitemporal, byte-identical replay |
| transport | CHORUS Fabric | Cross-region tensor spine (179 ms transatlantic, 4.45× bandwidth) |
| federation | PrismAPI | Cross-tenant `remote` nodes |

## The four gaps it fills

The Prism family is strong in the engine room and empty at the developer-facing top. ChorusGraph builds the four missing layers: **(a)** graph/DSL surface, **(b)** execution engine/scheduler, **(c)** tool calling, **(d)** human-in-the-loop + durable checkpointing + streaming.

## Guiding principles

- **ChorusGraph is native.** Product and FC*/HC* benchmarks run on `chorusgraph.core.Graph`. LangGraph is for FL*/HL* baselines only ([`docs/TERMINOLOGY.md`](docs/TERMINOLOGY.md)).
- **Safe cache before fast cache.** The skip-the-LLM decision uses a two-stage gate (coarse 64-d recall → full-precision verify); generative outputs are never replayed verbatim. See `DESIGN_v0.2.md` §8.
- **Measure, don't assert.** Cost/latency targets are experiments (hit rate `h`, overhead `o`, per-slug false-positive budget), not marketing numbers.

## Provenance

Productizes integration already dogfooded in production in `InsightitsAIAgent/meeting-scheduler/` (Website Hub, Dashboard Hub).

---

*Insight IT Solutions · native runtime in `chorusgraph/core/` · see [`docs/TERMINOLOGY.md`](docs/TERMINOLOGY.md)*
