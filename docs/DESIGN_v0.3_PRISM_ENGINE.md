# ChorusGraph — Prism Engine Architecture (v0.3)

**Status:** Active · replaces LangGraph as execution substrate  
**Builds on:** DESIGN v0.2 inventory + ADR-004 native runtime  
**Date:** 2026-07-02

---

## 1. Thesis

**ChorusGraph is the orchestration runtime for the entire Prism family.**

When documentation or conversation says **ChorusGraph**, it means the **native engine and full product stack** (`chorusgraph.core`), not LangGraph. See [`TERMINOLOGY.md`](TERMINOLOGY.md).

**Composition:** attach the full Prism product via [`ChorusStack`](COMPOSE.md) — defaults wire cache, memory, checkpoint, ledger, and tools; individual backends (e.g. Redis cache) are swappable without changing the engine.

LangGraph is a **comparison baseline only** (benchmark FL*, HL*) and a **legacy migration shim** (`wrap()`). It must not orchestrate FC*, HC*, or new product graphs.

One tenant-seeded **64-d vector substrate** (PrismLang JL projection) connects:

| Concern | Prism product | Tier |
|---------|---------------|------|
| Hop compression + audit | **PrismLang** | L0 |
| Semantic skip / LLM memo | **PrismCache** + **PrismResonance** scoring | L1 |
| KB retrieval + taxonomy | **PrismRAG** + pgvector | L2 |
| Cross-session memory | **PrismCortex** | L3 (data-layer service) |
| Same-container handoff | **PrismLang** `PrismEnvelope` | Transport — in-proc |
| Cross-container / cross-region | **CHORUS Fabric** | Transport — remote |
| Cross-tenant federated subgraph | **PrismAPI** over CHORUS | Transport — federated |
| Enterprise ops | **ChorusMesh** | Optional overlay |

---

## 2. Layered architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  APPLICATION — Graph DSL, Agents (ReAct/Reflection/Plan-Solve), Role nodes   │
├─────────────────────────────────────────────────────────────────────────────┤
│  CHORUSGRAPH ENGINE                                                          │
│  Graph compiler · Pregel scheduler · Policy engine · Route Ledger            │
│  Built-in nodes: ingress · cache_gate · retrieve · llm · tool · remote       │
├─────────────────────────────────────────────────────────────────────────────┤
│  TRANSPORT SPINE (per-edge, scheduler-selected)                              │
│  inproc → PrismLang envelope    chorus_local → CHORUS gRPC                   │
│  chorus_federated → PrismAPI    (manifest declares mode per edge)            │
├─────────────────────────────────────────────────────────────────────────────┤
│  PRISM DATA PLANE                                                            │
│  L0 PrismLang │ L1 Cache+Resonance │ L2 RAG │ L3 Cortex │ CHORUS │ Mesh     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 What replaces LangGraph

| LangGraph | ChorusGraph native |
|-----------|-------------------|
| `StateGraph` | `chorusgraph.graph.Graph` |
| Pregel super-steps | `chorusgraph.runtime.CompiledGraph` |
| `MemorySaver` / checkpointer | `PrismCheckpointer` (section snapshots — Phase 2) |
| Opaque state dict | **Section schema** + `PrismEnvelope` sequence |
| HTTP between services (DIY) | **CHORUS** + **PrismAPI** |
| Tool dispatch (DIY) | `chorusgraph.nodes.tool` + MCP (Phase 3) |

---

## 3. Transport spine — two (plus one) modes

The scheduler picks transport **per edge** from the deployment manifest or `add_edge(..., transport=)`.

### 3.1 `inproc` — same process (default)

**Product:** PrismLang  
**Mechanism:** After hop *H* writes artifact *A*, engine calls `transport.publish()`:

1. Project artifact text → 384-d embed → 64-d JL vector (reuse ingress `raw_embedding_384` when set)
2. Build `PrismEnvelope` with `rule_chain`, `agent_id=H`
3. Store artifact in session store keyed by `envelope_id`
4. Append envelope to `state.prism_sequence`

Downstream hop resolves via `transport.resolve(envelope_id)` — **bounded JSON**, not growing transcript.

**Code:** `chorusgraph/transport/inproc.py`, `chorusgraph/transport/envelope.py`

### 3.2 `chorus_local` — same cluster, different container/service

**Product:** CHORUS Fabric  
**Mechanism:** Serialize `PrismEnvelope` (+ artifact ref) into CHORUS gRPC tensor frame.
Receiver hydrates envelope into local session store before running the target node.

**When:** Researcher in pod A → Writer in pod B; bandwidth/latency win (179 ms p50 transatlantic, 4.45× bandwidth vs JSON).

**Code:** `chorusgraph/transport/chorus.py` — wired to `prism.cluster.transport.ClusterTransport`; `ChorusBatchFrame` is the wire unit (Improve-2 T6).

### 3.3 `chorus_federated` — different tenant / network

**Product:** PrismAPI over CHORUS  
**Mechanism:** `remote` node type declares `provider_id`; query template from state section;
response lands in `kb_context` with provider `category_slug`.

**When:** Legal KB on Tenant B, consumer graph on Tenant A.

**Code:** `chorusgraph/transport/prismapi.py` — wired to `prism.api.consumer.PrismAPIClient` loopback/HTTP (Improve-2 T7).

### 3.4 Spine selection flow

```
for each super-step (node N → node M):
    mode = edge.transport or manifest.transport.default
    if mode == inproc:
        InProcSpine.deliver(state, hop=N, artifact=...)   # PrismLang
    elif mode == chorus_local:
        ChorusSpine.deliver(state, frame=envelope_bytes)  # CHORUS
    elif mode == chorus_federated:
        PrismAPISpine.invoke(provider_id, query_section)    # PrismAPI
```

---

## 4. Memory & search tiers inside nodes

### 4.1 L0 — PrismLang (every hop)

- `@prism_node` or `transport.publish()` after each write
- `PrismProjector`: tenant-seeded 384→64
- `rule_chain` audit trail → Route Ledger

### 4.2 L1 — PrismCache + PrismResonance (cache_gate + LLM wrap)

**cache_gate node (before expensive children):**

| Stage | Space | Product |
|-------|-------|---------|
| Coarse recall | 64-d | PrismCache + **PrismResonance** `constructive_score` |
| Full verify | 384-d cosine | ChorusGraph `gate()` §8.1 |
| Policy gate | — | `CachePolicy` on `Section` |

On verified hit: skip retrieve + LLM (fast path). Resonance is **not optional** — it scores L1 candidates.

> **CacheProfile (H21):** per-node × category attributes (`keying`, `ttl_s`, `scope`, `risk_tier`) govern
> the gate — see [`CACHE_PROFILES.md`](CACHE_PROFILES.md). Healthcare judgment hops use fingerprint keying
> and quality-gated seeding; finance `fx_rates` uses semantic + short TTL.

**Code:** `chorusgraph/cache_gate/gate.py`, `cache_gate/backend.py`

### 4.3 L2 — PrismRAG + Resonance rerank (retrieve node)

**retrieve node (on cache miss):**

1. PrismRAG remap + pgvector → candidate chunks (taxonomy `category_slug`)
2. Project each chunk → 64-d (PrismLang JL) + **384-d cosine rerank** (same verify math as cache_gate stage 2)
3. L1 coarse recall uses **PrismResonance** `query()` constructive_score; L2 rerank uses projected 64-d cosine until chunks are pre-indexed in the resonance store (hub path)
4. Output → `kb_context` section (`REPLAY_SAFE` cache policy)

**Code:** `chorusgraph/nodes/retrieve.py`

### 4.4 L3 — PrismCortex (cross-session)

- **Tool role:** explicit `cortex.recall()` mid-turn
- **Ambient role:** async digest after response (zero added latency §13.3)
- Separate data-layer service — not inline in scheduler thread

**Code:** `chorusgraph/memory/cortex_service.py`, `async_digest.py`

---

## 5. Built-in node kinds → Prism mapping

| Node | Prism components | Transport |
|------|------------------|-----------|
| **vector_ingress** | PrismLang embed-once (384-d + 64-d) | — |
| **cache_gate** | L1 Cache + Resonance + sidecar | inproc |
| **retrieve** | L2 RAG + Resonance rerank | inproc |
| **llm** | L1 `get_or_call` + grounding guard | inproc |
| **tool** | Side-effect registry; results → envelope | inproc |
| **remote** | PrismAPI + CHORUS | chorus_federated |
| **router** | Taxonomy + 64-d rules first; LLM fallback | inproc |
| **compute** | Optional `@prism_node` | per edge |

---

## 6. One turn — full path (miss)

```
① Request
② vector_ingress     — PrismLang embed once
③ router             — taxonomy / rule_chain
④ cache_gate         — Resonance 64-d recall → 384-d verify
   ├─ HIT  → writer (envelope resolve) → respond
   └─ MISS ↓
⑤ retrieve           — PrismRAG + Resonance rerank
⑥ cortex.recall      — optional L3 facts
⑦ llm                — controller (customer-owned Gemini/etc.)
⑧ grounding guard    — citation + faithfulness (planned)
⑨ respond
   ╎ async: L1 cache write, Cortex digest
```

**Fast path (hit):** ①②③④⑤a⑧⑨ — skips ⑤⑥⑦.

---

## 7. PrismEngineContext — single DI bag

All nodes receive a shared `PrismEngineContext` (extends finance/healthcare runtime):

```python
@dataclass
class PrismEngineContext:
    tenant_id: str
    cache: PrismCache          # L1 + internal Resonance store
    sidecar: SidecarStore
    cortex: CortexMemoryService | None
    tool_registry: ToolRegistry
    session_artifacts: dict    # envelope_id → artifact
    chorus: ChorusClient | None
    prismapi: PrismAPIClient | None
```

**Code:** `chorusgraph/engine/context.py`

Graph compile: `g.compile(context=ctx)`

---

## 8. Package map (implementation)

| Path | Role |
|------|------|
| `chorusgraph/graph/` | Builder + IR |
| `chorusgraph/runtime/` | Scheduler (Pregel) |
| `chorusgraph/transport/` | Spine + PrismLang/CHORUS/PrismAPI |
| `chorusgraph/engine/` | `PrismEngineContext`, policy manifest |
| `chorusgraph/cache_gate/` | L1 two-stage gate |
| `chorusgraph/nodes/` | tool, retrieve, roles, agents |
| `chorusgraph/memory/` | L3 Cortex integration |
| `chorusgraph/transforms/` | Projector, templates, intent |
| `chorusgraph/sections/` | Section schema + CachePolicy |
| `chorusgraph/ledger/` | Route Ledger |
| `chorusgraph/adapter/` | Legacy LangGraph wrap (migration only) |

---

## 9. Build phases (replacement-first)

| Phase | Deliverable | Prism coverage |
|-------|-------------|----------------|
| **1** ✅ | Native Graph + scheduler | Engine shell |
| **1b** ✅ | Transport spine + envelope store | **PrismLang** in-proc |
| **2** | Edge transport manifest; migrate B/D/F graphs | Full in-proc path |
| **2b** | `retrieve` node + RAG driver hook | **PrismRAG + Resonance** |
| **2c** | Native checkpointer (section snapshots) | Postgres |
| **3** | CHORUS client in spine | **CHORUS Fabric** |
| **3b** | `remote` node + PrismAPI provider | **PrismAPI** |
| **4** | HITL interrupt + streaming | Engine |
| **5** | ChorusMesh hooks | **ChorusMesh** ops |

LangGraph dependency → `[legacy]` optional extra in pyproject.

---

## 10. Verification matrix

| Prism product | Engine touchpoint | Test |
|---------------|-------------------|------|
| PrismLang | demo_graph, transport.publish | `test_native_runtime`, `test_transport` |
| PrismCache+Resonance | cache_gate | `test_cache_gate` |
| PrismRAG | retrieve node | `test_retrieve` (Phase 2b) |
| PrismCortex | memory demos | `test_memory` |
| CHORUS | chorus spine | `test_chorus_spine` (mock) |
| PrismAPI | remote node | `test_prismapi_spine` (mock) |

---

## 11. Narrative (replacement)

LangGraph answers *how do I wire nodes in one process*. The **Prism engine** answers *how do I run
multi-agent systems where every hop is vector-addressed, cache-safe, auditable, and transport-aware*
— same container via PrismLang envelopes, different containers via CHORUS, federated knowledge via
PrismAPI, search inside nodes via PrismResonance, long memory via PrismCortex.

**No LangGraph required for execution.** Import adapter remains for migration only.

---

*Companion docs: DESIGN_v0.2.md (inventory), ADR-004-native-runtime.md, WORKFLOW.md*
