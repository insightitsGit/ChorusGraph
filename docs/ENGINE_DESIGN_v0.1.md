# ChorusGraph Execution Engine — Design v0.1 (engine-first, Prism-native)

> **Goal (non-negotiable):** ChorusGraph is a **complete replacement** for LangGraph, not a layer on
> top of it. The runtime, the communication fabric, the persistence, the observability — all owned by
> the Prism family. LangGraph is a *migration target we shim*, never a dependency we run on.
>
> **The replacement test:** `grep -rn "langgraph" chorusgraph/core/` returns **zero**. When that holds,
> ChorusGraph is a runtime, not a plugin.

Companion to [`DESIGN_v0.2.md`](DESIGN_v0.2.md). This doc defines the piece DESIGN_v0.2 was missing:
**the execution engine.**

---

## 0. The honest reframe

The earlier design borrowed `langgraph.graph.StateGraph` (engine) and wrapped `langgraph.checkpoint`
(persistence). That made ChorusGraph an *augmentation layer*, which is the opposite of the stated goal.

The correction is smaller than it looks. Surveying the real Prism assets, **almost every engine part
already exists and is Prism-native** — it was simply wired to LangGraph instead of to itself:

| Engine capability | Prism asset that already provides it | Status |
|---|---|---|
| Message / channel value | `prismlang.PrismEnvelope` (vector + `rule_chain` audit) | ✅ exists |
| Communication bus | `prismresonance.FrequencyBroadcast` / `InProcessBroadcast` / `RedisBroadcast` | ✅ exists |
| Semantic routing / search | `prismresonance.ResonanceEngine`, `dominant_frequency` | ✅ exists |
| Cross-machine transport (tensors) | **CHORUS** | ✅ exists (separate lib) |
| Cross-container federation | **PrismAPI** + `prismlang.BoundaryTranslator.translate` | ⚠️ PrismAPI separate repo, not yet wired |
| Checkpoint / persistence / time-travel | `prismlang.AsyncPostgresCheckpointer` (`aput_writes`, `aget_delta_channel_history`, `aprune`) | ✅ exists |
| Long-term memory | Cortex (`chorusgraph/memory`, `digest`/`recall`/`explain`, bitemporal) | ✅ exists |
| Semantic cache / skip | `chorusgraph/cache_gate`, `CachePolicy` | ✅ exists |
| Observability / trace | `chorusgraph/ledger` (`RouteLedger`, `LedgerStep`) | ✅ exists |
| Role-typed nodes | `chorusgraph/nodes/roles.py` (`RoleTemplate`, `Node.with_role`, Researcher/Writer/Validator) | ✅ exists |
| Agent patterns | `chorusgraph/agents` (`run_react`, `run_reflection`, `run_plan_solve`, `run_agent_loop`) | ✅ exists |
| **Super-step scheduler (the executor)** | **— none —** | ❌ **THIS is the missing piece** |

**Conclusion:** ChorusGraph does not need a from-scratch rewrite. It needs **one new component — the
scheduler** — plus a rewire so the existing Prism parts hang off *it* instead of off LangGraph.

---

## 1. Architecture — three layers, one owned engine

```
┌───────────────────────────────────────────────────────────────────────────┐
│  L3  AUTHORING SURFACE  (DSL — mirrors LangGraph for drop-in migration)     │
│      Graph() · add_node · add_edge · add_conditional_edges · Send · compile │
│      compat.langgraph shim  ── translate an existing LangGraph graph ──►     │
├───────────────────────────────────────────────────────────────────────────┤
│  L2  PRISM SERVICES  (native built-ins, not plugins)                        │
│      Role nodes (roles.py) · Patterns (react/reflection/plan_solve/loop)    │
│      Cortex memory · cache_gate · Route Ledger · belief policy (sections)   │
├───────────────────────────────────────────────────────────────────────────┤
│  L1  EXECUTION ENGINE  ◄── THE NEW COMPONENT (chorusgraph/core)             │
│      Superstep scheduler · state channels · reducers · interrupts · stream  │
│      Persistence: prismlang.AsyncPostgresCheckpointer (native)              │
├───────────────────────────────────────────────────────────────────────────┤
│  L0  COMMUNICATION FABRIC  (all inter-node messaging — Prism-native)        │
│      MESSAGE  = PrismLang PrismEnvelope   (vector-typed + rule_chain)        │
│      BUS      = Resonance FrequencyBroadcast (in-proc) / RedisBroadcast     │
│      SEARCH   = Resonance ResonanceEngine (dominant_frequency routing)      │
│      TRANSPORT= CHORUS (cross-machine tensor shipping)                       │
│      FEDERATE = PrismAPI + BoundaryTranslator (cross-container agents)       │
└───────────────────────────────────────────────────────────────────────────┘
```

**Rule:** every arrow between two nodes is an **envelope on the bus**, never a raw dict. This is the
architectural line that separates ChorusGraph from LangGraph.

---

## 2. L0 — The communication fabric (your explicit mandate)

> *All communication in the engine is PrismLang + CHORUS + Resonance; cross-container multi-agent is PrismAPI.*

### 2.1 Message = `PrismEnvelope`
Every value a node emits is wrapped as a `PrismEnvelope`:
```
turn_id: int          # chronological index within the thread
agent_id: str         # the node/role that produced it
category_slug: str    # taxonomy category (routing key)
vector: List[float]   # PrismLang projection of the payload
rule_chain: List[str] # immutable provenance — free audit trail per hop
```
Dict-state (LangGraph's channel value) is replaced by **envelope channels**. `rule_chain` gives the
engine provenance for free — something LangGraph structurally cannot provide.

### 2.2 Bus = Resonance broadcast
Nodes are **agents on the Resonance bus**. The scheduler wires them at compile time:
- `register_agent(node_id)` — node joins the bus.
- `set_frequency(node_id, category_slug)` — node tunes to the taxonomy it consumes.
- `broadcast(envelope)` — a node's output is published, not handed to one successor.
- `dominant_frequency()` / `get_frequencies()` — **Resonance decides who resonates** with an envelope.

This is how edges work natively: a static edge is a fixed subscription; a **conditional edge is a
Resonance match** — the next node is whoever's frequency the emitted envelope most strongly excites.
Priority bands (`EMERGENCY/ALERT/NORMAL/NEUTRAL/RECOVERY/ARCHIVE`) give the scheduler native
back-pressure and interrupt precedence.

- **Single runtime:** `InProcessBroadcast` (zero-copy, same process).
- **Distributed (one cluster):** `RedisBroadcast` (multi-process/machine, same trust domain).

### 2.3 Transport = CHORUS
When a super-step spans machines, envelopes cross the wire as **CHORUS tensors** (the 4–5× bandwidth /
179 ms transatlantic path), not JSON. The scheduler is **location-transparent**: a node doesn't know
if its subscriber is in-process or across an ocean — the bus + CHORUS resolve it.

### 2.4 Federation = PrismAPI (cross-container multi-agent)
When agents live in **separate containers / services** (different trust domains, deploys, or teams),
they federate over **PrismAPI**, with `BoundaryTranslator.translate` re-projecting envelopes across the
boundary (tenant seed / dimension differences). PrismAPI is the *only* sanctioned cross-container hop —
the in-runtime Resonance bus never crosses a container boundary directly.

```
  in-runtime agents ──Resonance bus──► [scheduler] ──CHORUS──► same-cluster machine
        container A  ──────────────── PrismAPI (federated) ──────────────►  container B
                                    (BoundaryTranslator re-projects envelopes)
```

**Decision rule for a multi-agent edge:**
| Agents are… | Communication path |
|---|---|
| same process | Resonance `InProcessBroadcast` |
| same cluster, different machine | Resonance `RedisBroadcast` + CHORUS transport |
| different container / trust domain | **PrismAPI** + `BoundaryTranslator` |

---

## 3. L1 — The execution engine (the one thing we build)

A **bulk-synchronous (Pregel/BSP) super-step scheduler**, living in `chorusgraph/core/`.

### 3.1 The super-step loop
```
compile(): register every node on the Resonance bus; bind reducers per channel.
invoke(input):
  1. seed input as envelope(s); active := {entry nodes}
  2. SUPER-STEP:
     a. run all `active` nodes CONCURRENTLY (async) — each reads its channels, returns envelope updates
     b. WRITE PHASE: apply per-channel reducers to merge all updates (deterministic order)
     c. broadcast merged envelopes on the bus
     d. next-active := nodes whose frequency the merged envelopes excite (Resonance) OR static-edge targets
     e. checkpoint(super_step, channel_versions) → prismlang.AsyncPostgresCheckpointer.aput
     f. if next-active empty OR END reached OR recursion_limit hit → STOP, else active := next-active; repeat
  3. return final channel values
```
- **Parallelism** = every node in `active` runs in the same super-step (fan-out is free).
- **Cycles/loops** = a node re-entering `active` in a later super-step (ReAct/Reflection loops).
- **Fan-out (Send-equivalent)** = one node broadcasts N envelopes on N frequencies → N nodes activate.
- **Determinism** = reducers apply in a fixed channel order; `rule_chain` records the exact merge.

### 3.2 State & channels
- State schema = typed `TypedDict` (as today), but each field is an **envelope channel**.
- Reducers = `Annotated[T, reducer]` (mirror LangGraph's `operator.add`), applied in the WRITE PHASE.
- Channel versioning = the checkpointer's `aget_delta_channel_history` gives per-channel version history →
  native **time-travel** without a bespoke store.

### 3.3 Persistence & time-travel = PrismLang checkpointer (native)
Delete `chorusgraph/checkpoint/prism.py`'s LangGraph wrapper. Use `prismlang.AsyncPostgresCheckpointer`
directly:
- `aput` / `aput_writes` — checkpoint at each super-step boundary (+ pending writes for interrupts).
- `aget_tuple` / `alist` — resume a thread from any checkpoint.
- `aget_delta_channel_history` — **time-travel / `update_state`** (fork a run from a past channel state).
- `aprune` / `adelete_thread` — retention.
- `acopy_thread` — branch a run (what-if / A-B on the same history).

### 3.4 Human-in-the-loop (interrupts)
`interrupt_before` / `interrupt_after` / dynamic `interrupt()` are **super-step boundary halts**:
1. scheduler reaches a node marked interrupt → writes checkpoint + pending writes, then **suspends** and
   returns control with the current state.
2. human approves / edits (`update_state` → new checkpoint via delta history).
3. `invoke(None, thread_id)` **resumes** from the checkpoint — engine re-hydrates channels and continues.
No LangGraph `interrupt` needed; it falls out of checkpoint-at-boundary + resume.

### 3.5 Streaming
The scheduler emits an **event stream** as it runs (from the bus, not bolted on):
- `values` — full channel state after each super-step.
- `updates` — per-node envelope deltas as they broadcast.
- `messages` — token stream from LLM nodes.
- `debug` — super-step / reducer / Resonance-routing events (feeds Route Ledger + a future Studio).

### 3.6 Tool calling
Native `ToolNode` (`chorusgraph/nodes/tool.py`) + a `tools_condition` conditional edge (a Resonance
match on a "tool-request" frequency). ReAct/Reflection/Plan-Solve loops (§4) drive it.

---

## 4. L2 — Prism services as native built-ins (where your specified pieces live)

These already exist; the engine makes them **built-ins**, not adapters:

- **Role agents** (`chorusgraph/nodes/roles.py`): `Node.with_role(RoleTemplate)` — a `RoleTemplate`
  carries *prompt + tools + output target*. Prebuilt `ResearcherNode`/`WriterNode`/`ValidatorNode`;
  `promote(node, role)` upgrades any node. **In multi-agent, each role node is a Resonance-bus agent**
  tuned to the category it consumes — the supervisor/swarm topology is just their subscription graph.
- **Agent patterns** (`chorusgraph/agents`): `run_react`, `run_reflection`, `run_plan_solve`,
  `run_agent_loop` (Reasoner/Actor/Router protocol). Each pattern is a **sub-graph of super-steps**;
  its loop is cycle-in-the-scheduler, its scratchpad is an envelope channel, its trace → `rule_chain`.
- **Cortex memory**: `recall` at ingress (long-term context), `digest` at egress (write-back) — native
  channels, not tool calls.
- **cache_gate**: see §5 — promoted from a node to an **engine-level node-entry interceptor**.
- **Route Ledger**: see §6 — the engine's native trace.
- **Belief policy** (`sections` / `policy`): `PlanPolicy` knobs (`confidence_stop`, `groundedness_floor`)
  read by the scheduler to decide early-stop / abstain between super-steps.

---

## 5. Cache-gate as a native channel interceptor (the real "skip" win)

Today the cache is a *node* you route around (the healthcare-D fix). Natively, the engine consults the
gate at **node entry**:
```
before running node N with input envelope E:
    if N.cache_policy != NO_CACHE:
        hit = cache_gate.gate(E, policy=N.cache_policy)   # 64-d coarse → 384-d verify
        if hit: emit hit.value as N's output, SKIP execution (0 LLM), record cache_hit on the LedgerStep
```
This makes "skip the LLM call" a **first-class engine behavior** for every node, not a hand-wired
detour — which is exactly what the C-vs-D benchmark needed and couldn't get from a bolt-on.

---

## 6. Route Ledger = the native trace (no LangSmith, no adapter)

Delete `chorusgraph/adapter/wrap.py` ("non-invasive LangGraph adapter"). The scheduler writes a
`LedgerStep` per node per super-step directly: `node`, `edge_taken`, `rule_chain`, `duration_ms`,
`cache_hit`, `cache_score`, `grounding_score`. The `RouteLedger` (run_id, tenant_id, graph_id, steps)
is the built-in observability — LangSmith-equivalent, owned, and fed by `rule_chain` provenance.

---

## 7. L3 — Authoring surface & migration

Public API mirrors LangGraph **on purpose**, so existing code is a drop-in:
```python
from chorusgraph import Graph, END, START      # not langgraph.graph
g = Graph(State)
g.add_node("intake", intake); g.add_role_node("writer", WriterNode())
g.add_edge(START, "intake")
g.add_conditional_edges("intake", route)        # route == Resonance match under the hood
app = g.compile(checkpointer=prism_postgres())  # PrismLang checkpointer
app.invoke(x, thread_id=...) / app.stream(...) / app.get_state(...) / app.update_state(...)
```
**Migration shim** — `chorusgraph.compat.langgraph`: consume an existing `StateGraph` definition and
re-emit it onto the ChorusGraph engine (leveraging `BoundaryTranslator.as_langgraph_node` in reverse).
This is the embrace-then-replace path: a LangGraph user swaps one import and runs on ChorusGraph.

---

## 8. The LangGraph-deletion debt (tracked to zero)

Every current dependency is a debt with an owner:
| File | Today | Replace with |
|---|---|---|
| `chorusgraph/checkpoint/prism.py` | wraps `langgraph.checkpoint.SqliteSaver/PostgresSaver` | `prismlang.AsyncPostgresCheckpointer` |
| `chorusgraph/examples/**/graph.py` | `langgraph.graph.StateGraph` | `chorusgraph.Graph` (L3) |
| `chorusgraph/adapter/wrap.py` | "non-invasive LangGraph adapter" | native Route Ledger in scheduler (§6) |
| benchmark `container_b/d` | `from langgraph.graph import StateGraph` | ChorusGraph engine (re-benchmark on real runtime) |

> **Benchmark consequence:** the current A/B and C/D numbers compare *LangGraph* vs *LangGraph+Prism-layer*.
> They must be re-run on the ChorusGraph engine before any "replacement" claim — otherwise we're
> measuring a plugin, not a runtime.

---

## 9. Build phases (the scheduler is the critical path)

1. **P1 — Engine core:** `chorusgraph/core` super-step scheduler + envelope channels + reducers, over
   `InProcessBroadcast`. DSL (`Graph`, `compile`, `invoke`). *Exit:* a graph runs with zero `langgraph`.
2. **P2 — Persistence:** wire `prismlang.AsyncPostgresCheckpointer`; resume + time-travel via delta history.
3. **P3 — HITL + streaming:** interrupts as boundary halts; the 4 stream modes.
4. **P4 — Cache interceptor + Route Ledger** native (§5, §6).
5. **P5 — Distribution:** `RedisBroadcast` + CHORUS transport (multi-machine super-steps).
6. **P6 — Federation:** PrismAPI + `BoundaryTranslator` for cross-container multi-agent.
7. **P7 — Migration shim + re-benchmark** on the real engine; then the "replacement" claim is earned.

---

## 10. Definition of done (the replacement is real when…)

- [ ] `grep -rn langgraph chorusgraph/core` == 0; examples import `chorusgraph.Graph`.
- [ ] Persistence, resume, time-travel, interrupts, streaming all run on Prism-native components.
- [ ] Multi-agent role graph runs over the Resonance bus in-proc, CHORUS cross-machine, PrismAPI
      cross-container — same graph definition, three transports, chosen by the §2.4 rule.
- [ ] Cache-skip is an engine node-entry behavior; Route Ledger is the native trace.
- [ ] A real LangGraph graph runs unmodified through `compat.langgraph` on the ChorusGraph engine.
- [ ] A/B and C/D benchmarks re-run on the engine — the delta now isolates *ChorusGraph the runtime*.

---
*v0.1 · engine-first · the only net-new component is the L1 scheduler; everything else is rewiring
existing Prism-native parts off LangGraph and onto the engine.*
