# ChorusGraph Developer Guide

> **Terminology:** **ChorusGraph** = native engine + full product stack. **Not LangGraph.** See [`TERMINOLOGY.md`](TERMINOLOGY.md).
>
> **Composition:** [`COMPOSE.md`](COMPOSE.md) — `ChorusStack` attaches Prism defaults; swap cache, memory, checkpoint, ledger, or tools per port.

Standard patterns for building agents on **`chorusgraph.core.Graph`**.

## Contents

| § | Topic |
|---|--------|
| 1 | Mental model |
| 2 | Minimal graph |
| 3 | State |
| 4 | Routing |
| 5 | Cache (semantic skip) |
| 6 | Route Ledger |
| 7 | Checkpoints & interrupts |
| 8 | Streaming |
| 9 | Benchmark scenario naming |
| **10** | **Planning & reasoning** |
| **11** | **Execution patterns (ReAct / Plan-Solve / Reflection)** |
| **12** | **Domain performance playbook** |
| **13** | **Multi-agent pipelines** |
| **14** | **Measuring & tuning** |
| 15 | Further reading |

**Demos (no LangGraph):**

```bash
chorusgraph-demo                    # routing + ledger (LLM-free)
chorusgraph-finance-patterns        # ReAct, Plan-Solve, Reflection (needs GEMINI_API_KEY)
```

Reference graphs: `chorusgraph/examples/finance_agent/patterns_graph.py`, `benchmark/fc1/`, `benchmark/hc2/`.

---

## 1. Mental model

```python
from chorusgraph import ChorusStack, Graph, START, END

stack = ChorusStack.defaults(tenant_id="my-tenant")  # full Prism product
compiled = graph.compile(stack=stack)
```

Override one backend without touching the engine — see [`COMPOSE.md`](COMPOSE.md).

| Concept | What it is |
|---------|------------|
| **Graph** | Declarative builder: nodes, edges, `compile()` |
| **NodeContext** | Per-invocation read/publish API (`ctx.read()`, `ctx.publish(...)`) |
| **Channel state** | Merged dict in `_scalars` + envelope sequence — **not** raw LangGraph reducers |
| **Envelope** | Every hop publishes a `PrismEnvelope` (vector + `category_slug` + artifact) |
| **Resonance bus** | Routes conditional edges when **one** subscriber matches the envelope slug |
| **Router fn** | Fallback when Resonance is ambiguous (multiple subscribers on same slug) |

**Rule:** nodes talk through `ctx.publish(artifact={...})`, not `return {"key": value}` dicts.

## 2. Minimal graph

```python
from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import NodeContext
from chorusgraph.core.channels import NodeUpdate

def analyze(ctx: NodeContext) -> NodeUpdate:
    msg = ctx.read().get("message") or ""
    return ctx.publish(
        artifact={"score": len(msg), "raw_output": msg},
        category_slug="general",
    )

def route(ctx: NodeContext) -> NodeUpdate:
    score = int(ctx.read().get("score") or 0)
    slug = "long_path" if score > 5 else "short_path"
    return ctx.publish(artifact={"route": slug}, category_slug=slug)

g = Graph(tenant_id="my-tenant", graph_id="demo")
g.add_node("analyze", analyze)
g.add_node("route", route)
g.add_node("short", lambda c: c.publish(artifact={"response": "short"}, category_slug="short_path"), category_slug="short_path")
g.add_node("long", lambda c: c.publish(artifact={"response": "long"}, category_slug="long_path"), category_slug="long_path")
g.add_edge(START, "analyze")
g.add_edge("analyze", "route")
g.add_conditional_edges("route", lambda v: v.get("route", "short"), {"short_path": "short", "long_path": "long"})
g.add_edge("short", END)
g.add_edge("long", END)

out = g.compile().invoke({"message": "hello world"})
```

See also: `chorusgraph/examples/demo_graph.py` (LLM-free routing demo).

## 3. State — what persists between nodes

`ctx.read()` returns `ChannelState.view()`:

| Type | Persisted via `publish(artifact=...)` | Notes |
|------|--------------------------------------|-------|
| `str`, `int`, `float`, `bool`, `None` | Yes | Stored in `_scalars` |
| `dict` | Yes | Copied into `_scalars` (e.g. `pending_action`) |
| `list` | Yes | Replaced unless key is in `APPEND_LIST_SCALAR_KEYS` (`retrieved`, `conversation_history`, …) |
| Custom objects (e.g. dataclasses) | **Input only** | Put on `invoke({...})`; kept in `_scalars` if set at input |

**Common pitfall:** publishing only scalars worked before v0.11; dict/list fields (`pending_action`, `retrieved`) must be in the artifact — the engine now persists them. Always `int()` / `bool()` when reading numeric/boolean fields that may arrive as strings from JSON checkpoints.

```python
def _view(ctx: NodeContext) -> dict:
    v = ctx.read()
    v["step"] = int(v.get("step") or 0)
    v["done"] = bool(v.get("done"))
    return v
```

## 4. Routing

### 4.1 Conditional edges (deterministic router)

Use when nodes share a generic slug (e.g. `"general"`):

```python
g.add_conditional_edges(
    "react",
    lambda v: "tool" if v.get("pending_action") else "writer",
    {"tool": "tool", "writer": "writer", "react": "react"},
)
```

Resonance is **skipped** when multiple successors share the same frequency; the **router fn** decides.

### 4.2 Resonance routing (envelope slug)

Register distinct `category_slug` per successor:

```python
g.add_node("left", left_fn, category_slug="left")
g.add_node("right", right_fn, category_slug="right")
g.add_conditional_edges("route", lambda _: "missing", {"path_a": "left", "path_b": "right"})
# route node: ctx.publish(..., category_slug="left")  → routes via bus
```

### 4.3 Fan-out

```python
g.add_fan_out("split", "worker_a", "worker_b")  # same super-step
```

## 5. Cache (semantic skip)

Finance and healthcare benchmarks share the same **cache_gate** shape; **what** you cache differs by domain (see §12).

1. **`vector_ingress`** — project query once (`raw_embedding_384` / `query_vector_64`); reuse on every hop
2. **`cache_gate` node** — `chorusgraph.cache_gate.gate()` two-stage lookup (64-d coarse → 384-d verify)
3. **On hit** — restore payload, **conditional route** to writer (skip expensive hops)
4. **On miss** — run agent / retrieval pipeline, **seed cache** after quality gates pass

```python
from chorusgraph.cache_gate import gate, seed_cache_entry
from chorusgraph.sections.models import CachePolicy, Section
from chorusgraph.sections.profiles import default_registry

profile = default_registry().get("fx_rates")  # semantic · 1h TTL · global · low risk
section = Section(
    section_id="fx_lookup",
    category_slug="fx_rates",
    content=query_text,
    cache_policy=CachePolicy.REPLAY_SAFE,
)
decision = gate(
    query_text,
    section,
    cache_backend,
    sidecar,
    coarse_threshold=0.80,
    verify_threshold=0.85,
    profile=profile,
    tenant_id="my-tenant",
    raw_embedding_384=state.get("raw_embedding_384"),
    projected_vector_64=state.get("query_vector_64"),
)
if decision.is_hit:
    tool_result = decision.value
else:
    ...  # run tools / agents, then seed_cache_entry(...) on success
```

**Finance (FC1/FC2):** whole-answer skip on repeat FX queries — ~3–4× latency wins when Gemini dominates cost.

**Healthcare (HC1/HC2):** **facts-only** cache (retrieval, drug interactions) — judgment hops (`analyze`, `safety`, `writer`) always re-run. See [`CACHE_PROFILES.md`](CACHE_PROFILES.md).

Without cache, ChorusGraph vs LangGraph latency differs only by engine overhead (~1–5%) because **the LLM dominates**.

## 6. Route Ledger

```python
from chorusgraph import SqliteLedgerSink, wrap

compiled = g.compile()
wrapped = wrap(compiled, tenant_id="t", graph_id="my-graph", sink=SqliteLedgerSink(":memory:"))
result = wrapped.invoke({"message": "hi"})
ledger = wrapped.last_ledger  # LedgerStep list: node, route_via, cache_hit, duration_ms
```

## 7. Checkpoints & interrupts

```python
from chorusgraph.core.persistence import json_file_checkpointer

cp = json_file_checkpointer(".chorusgraph/cp")
compiled = g.compile(checkpointer=cp)
config = {"configurable": {"thread_id": "t1"}}

out = compiled.invoke({"seed": 1}, config=config)          # static interrupt_after
out = compiled.invoke({"__resume__": answer}, config=config)  # dynamic HITL resume
```

## 8. Streaming

```python
for event in compiled.stream({}, stream_mode="updates"):
    ...  # live per-node events (not batch replay)

for chunk in compiled.stream({}, stream_mode="messages"):
    ...  # token chunks via ctx.emit(chunk) inside nodes
```

## 9. Benchmark scenario naming

See [`TERMINOLOGY.md`](TERMINOLOGY.md) for the full policy. Summary:

| Letter | Framework |
|--------|-----------|
| **F** / **H** | Finance / Healthcare |
| **L** | LangGraph baseline only (FL*, HL*) |
| **C** | **ChorusGraph native only** (FC*, HC*) — `chorusgraph.core.Graph`, no `langgraph` imports |

Fair comparison requires **matching capabilities** (cache on/off, same tools, same prompts). See `benchmark/hc1/PARITY.md`.

Enforced in CI: `tests/test_fc_hc_no_langgraph.py`.

---

## 10. Planning & reasoning

ChorusGraph has **no separate “planning engine” box**. Planning is composed from three layers:

| Layer | What it is | When to use |
|-------|------------|-------------|
| **Graph topology** | Nodes + conditional edges = the plan | Known pipelines (finance multi-agent, clinical intake→analyze→writer) |
| **LLM nodes** | Chain-of-thought inside prompts | Single-hop reasoning, structured JSON outputs |
| **`chorusgraph.agents`** | Dynamic loops: reason ↔ act ↔ route | Novel multi-step tasks, tool use, plan-then-execute |

```
Turn
  → Router / cache_gate          (coarse path selection)
  → EITHER graph nodes           (static multi-agent plan)
  → OR Agent(pattern=...)        (ReAct / plan_solve / reflection)
  → grounding guard + Route Ledger (every thought/action logged)
```

**Stance (product default):** deterministic graph routing first — cacheable and auditable. Drop into `Agent` only when the task needs dynamic multi-step reasoning.

**Observability:** inspect `agent_trace`, `rule_chain`, and Route Ledger steps — not a black-box planner.

```python
from chorusgraph import SqliteLedgerSink, wrap

wrapped = wrap(compiled, tenant_id="t", graph_id="g", sink=SqliteLedgerSink(":memory:"))
result = wrapped.invoke({"message": "Compare USD/EUR and USD/GBP"})
for step in result.get("agent_trace") or []:
    print(step["kind"], step["content"][:120])
for ls in wrapped.last_ledger.steps:
    print(ls.node, ls.duration_ms, ls.cache_hit)
```

**`PlanPolicy`** (budgets, not belief knobs yet):

```python
from chorusgraph.agents import PlanPolicy

policy = PlanPolicy(max_steps=8, token_budget=8000, on_exhaust="abstain")
```

Belief-tier knobs (`confidence_stop`, `groundedness_floor`) exist in `BeliefPolicy` but are **disabled until signals are calibrated** — enabling them raises `BeliefPolicyNotCalibratedError`.

---

## 11. Execution patterns (ReAct / Plan-Solve / Reflection)

All three patterns use one substrate (`run_agent_loop`) behind `Agent(pattern=...)`.

| Pattern | Best for | Stop condition |
|---------|----------|----------------|
| **`react`** | Unknown tool sequence, comparisons, exploration | LLM sets `finish=true` or `max_steps` / token budget |
| **`plan_solve`** | Decomposable tasks with known tool catalog | Static plan emitted upfront, sequential execution |
| **`reflection`** | Quality-sensitive drafts (rates, figures, citations) | Validator / grounding guard passes or `max_revisions` |

### Standalone agent (no full graph)

```python
from chorusgraph.agents import Agent, PlanPolicy, ReActOpts
from chorusgraph.nodes.tool import ToolRegistry

registry = ToolRegistry()
# registry.register("fetch_exchange_rate", ...)  # your tools

agent = Agent(
    pattern="react",
    tools=registry,
    model=your_llm_json_fn,  # (system, user) -> JSON string
    policy=PlanPolicy(max_steps=6),
    pattern_opts=ReActOpts(max_tool_calls=6, require_tool_before_finish=False),
)
result = agent.run("What is USD/EUR today?")
print(result.finished, result.finish_reason)
print([s.to_dict() for s in result.trace])
```

### Drop into a native graph

```python
from chorusgraph.core import Graph, START, END
from chorusgraph.core.node import dict_node_adapter
from chorusgraph.agents import Agent, AgentNode, PlanPolicy
from chorusgraph.examples.finance_agent.pattern_nodes import make_react_agent_handler
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

runtime = FinanceRuntime(tenant_id="finance-demo")
graph = Graph(tenant_id="finance-demo", graph_id="react-only")

graph.add_node(
    "react_agent",
    dict_node_adapter(make_react_agent_handler(runtime, policy=PlanPolicy(max_steps=6)), hop="react_agent"),
)
graph.add_edge(START, "react_agent")
graph.add_edge("react_agent", END)

out = graph.compile().invoke({"message": "USD to EUR rate?", "tool_calls": [], "rule_chain": []})
```

### Full finance pattern graph (cache + ReAct + validator)

Run the bundled demo:

```bash
pip install "chorusgraph[gemini]"
export GEMINI_API_KEY=...
chorusgraph-finance-patterns
```

Source: `chorusgraph/examples/finance_agent/patterns_graph.py` — three graphs:

- `build_react_graph()` — cache hit → writer; miss → ReAct → writer → validator
- `build_plan_solve_graph()` — static planner → tools → writer
- `build_reflection_graph()` — plan + writer + reflection validator loop

Topology (ReAct):

```
START → vector_ingress → cache_gate ─┬─ hit ──────────────→ writer → validator → END
                                     ├─ compound intent ──→ compound_tool → writer
                                     └─ miss ─────────────→ react_agent → writer
```

---

## 12. Domain performance playbook

Performance is **domain-shaped**. The same engine; different cache profiles, graph topology, and reasoning patterns. Profiles live in `chorusgraph/sections/profiles.default.json` — see [`CACHE_PROFILES.md`](CACHE_PROFILES.md) for the four archetypes.

### Quick picker

| Your domain | Archetype | Cache strategy | Graph pattern | Reasoning | Expected win |
|-------------|-----------|----------------|---------------|-----------|--------------|
| **Finance / rates / pricing** | B — smooth + volatile | Semantic whole-answer, **short TTL** (`fx_rates`: 1h) | `cache_gate` → ReAct or plan-solve → writer | ReAct for multi-pair; plan-solve for fixed steps | **High** — skip LLM on repeats (~ms vs seconds) |
| **Healthcare / legal / compliance** | C — brittle + stable | **Facts-only** cache; **never** cache judgment | intake → retrieve ∥ drug_check → analyze → safety → writer | Static multi-agent; `analyze` always fresh | **Medium** — mid-pipeline fact cache + parallel hops |
| **FAQ / docs / support** | A — smooth + stable | Semantic whole-answer, long/no TTL | cache_gate → writer (or template) | Minimal LLM | **Highest** cache hit rate |
| **Personalized / account context** | D — context-bound | **User/session scoped** keys (`user_profile`) | memory recall at ingress + scoped cache | Graph + Cortex recall | Isolation + correct hits per user |

### Finance — maximize latency & token savings

**Do:**

- Project embedding **once** at `vector_ingress`; pass `raw_embedding_384` through state
- Route cache hits **directly to writer** (skip researcher / ReAct)
- Use `category_slug` per intent: `fx_rates`, `compound_savings`, `user_profile`
- Seed cache **after successful tool calls** (see `seed_fx_cache_from_tool_calls` in finance nodes)
- Prefer `compound_tool` (deterministic CPU) over LLM for savings math

**Don't:**

- Re-embed on every hop
- Use global cache for user-specific profile payloads (`scope: user`)
- Expect big wins without `cache_gate` — Gemini dominates cold path

```python
from chorusgraph.examples.finance_agent.nodes import route_after_cache_pattern, make_cache_gate_handler
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

runtime = FinanceRuntime(tenant_id="finance-tenant")
graph.add_node("vector_ingress", ...)
graph.add_node("cache_gate", dict_node_adapter(make_cache_gate_handler(runtime), hop="cache_gate"))
graph.add_conditional_edges(
    "cache_gate",
    route_after_cache_pattern,
    {"writer": "writer", "compound_tool": "compound_tool", "react_agent": "react_agent"},
)
```

Default profiles (finance slugs):

| Slug | keying | ttl | scope | risk |
|------|--------|-----|-------|------|
| `fx_rates` | semantic | 3600s | global | low |
| `compound_savings` | semantic | none | global | low |
| `user_profile` | semantic | none | **user** | low |

### Healthcare — maximize safety *and* throughput

**Do:**

- Cache **retrieval** and **drug_check** artifacts globally (`clinical_retrieval`, `clinical_guidelines`)
- Use **fingerprint** keying on clinical facts (drugs, topic, pipeline depth) — not raw text alone
- Always re-run **`analyze`** and **`safety`** — judgment is never replayed from cache
- Use **PrismRAG** + vector retrieve for HC scenarios (`PrismRAGRetrievalBackend` on `ChorusStack`)
- Fan out independent hops (`retrieve` ∥ `drug_check`) where the graph allows
- Enable **quality-gated seeding** — do not seed abstain/refusal chains

**Don't:**

- Cache whole clinical recommendations (archetype C violation)
- Silo cache per session for global facts (caused HC1 0% hits historically)
- Expect finance-scale whole-answer skip rates — by design, judgment stays fresh

```python
from chorusgraph.sections.profiles import default_registry

profile = default_registry().get("clinical_retrieval")  # semantic · 30d · global · low
# Clinical gate: fingerprint keying + facts-only restore (retrieve, drug_check).
# See benchmark/hc2/nodes.py and benchmark/shared/healthcare_cache.py for the reference wiring.
# analyze_node always calls the LLM — judgment is never replayed from cache.
```

Default profiles (clinical slugs):

| Slug | keying | ttl | scope | risk |
|------|--------|-----|-------|------|
| `clinical_retrieval` | semantic | 30d | global | low |
| `clinical_judgment` | fingerprint | none | session | **high** |

Pipeline depth matters: a depth-6 case needs cached retrieve **and** interaction artifacts — `cache_payload_sufficient()` rejects shallow hits.

### FAQ / documentation — maximize hit rate

```python
from chorusgraph.sections.models import CacheProfile

faq_profile = CacheProfile(
    keying="semantic",
    ttl_s=None,           # stable content
    scope="global",
    risk_tier="low",
)
registry = default_registry()
registry.register("product_faq", faq_profile)
```

Graph: `cache_gate → writer` with `CachePolicy.REPLAY_SAFE` on low-risk categories.

### Personalized assistants — maximize correctness

```python
profile = default_registry().get("user_profile")  # scope=user
decision = gate(
    query_text,
    section,
    cache_backend,
    sidecar,
    profile=profile,
    tenant_id=tenant_id,
    session_id=session_id,
    user_id=user_id,  # required for user-scoped keys
    ...
)
```

Add Cortex recall at retrieve or ingress when answers depend on prior sessions — see `chorusgraph/examples/finance_agent/run_memory_demo.py`.

### Cold-path debugging (all domains)

Run benchmarks without cache to surface real LLM/safety gaps:

```bash
python -m benchmark.run_scenarios --scenarios FC1,HC2 --tasks 12 --no-cache
```

---

## 13. Multi-agent pipelines

Multi-agent = **role-typed nodes** wired by graph edges, not a separate orchestration framework.

| Role | Module | Typical job |
|------|--------|-------------|
| Researcher | `ResearcherNode` | Tool planning, ReAct |
| Writer | `WriterNode` | Final user-facing text |
| Validator | `ValidatorNode` | Grounding, reflection |

### Finance multi-agent (reference: FC2 / Container F)

```
MISS:  ingress → cache_gate → researcher → tool → writer → validator
HIT:   ingress → cache_gate ──────────────→ writer → validator
```

See [`FINANCE_MULTIAGENT_CHORUS.md`](FINANCE_MULTIAGENT_CHORUS.md) — conditional routing after `cache_gate` is the critical performance fix.

### Healthcare multi-agent (reference: HC2)

```
intake → retrieve ─┐
                   ├→ analyze → safety → writer
      drug_check ──┘
```

- **`analyze`** = reasoning hop (structured `reasoning` JSON)
- **`safety`** = evaluator / abstain gate
- Cache restores facts into state before `analyze` runs

```python
# Simplified analyze hop pattern (see benchmark/hc2/nodes.py)
def analyze_node(state):
    hop_artifacts = state.get("hop_artifacts") or {}
    retrieved = state.get("retrieved") or []
    artifact = llm_json(system=ANALYZE_SYSTEM, user=analyze_handoff_plain(hop_artifacts, retrieved))
    return {
        "analysis": artifact.get("reasoning"),
        "hop_artifacts": {**hop_artifacts, "analyze": artifact},
        "rule_chain": ["analyze=complete"],
    }
```

---

## 14. Measuring & tuning

### Thresholds — measure, don't guess

```bash
python -m benchmark.run_profiler    # sensitivity / volatility probes → CacheProfile suggestions
chorusgraph-audit --log queries.jsonl   # estimate hit rate on your traffic (no API key)
```

Finance benchmarks use measured coarse/verify thresholds via `chorusgraph.cache_gate.thresholds.measured_thresholds()` — not demo defaults (0.82/0.85).

### Route Ledger — production tuning

```python
from chorusgraph import SqliteLedgerSink, wrap

wrapped = wrap(compiled, tenant_id="t", graph_id="prod", sink=SqliteLedgerSink(".chorusgraph/ledger.db"))
wrapped.invoke(state)
for step in wrapped.last_ledger.steps:
    print(step.node, step.duration_ms, step.cache_hit, step.cache_score, step.rule_chain)
```

After a pilot:

```bash
chorusgraph-audit --list-runs --ledger-db .chorusgraph/ledger.db
chorusgraph-audit --ledger <run_id> --ledger-db .chorusgraph/ledger.db
```

### Performance checklist

| Check | Finance | Healthcare |
|-------|---------|------------|
| Embed once per turn | ✅ `vector_ingress` | ✅ vector ingress |
| Cache gate before LLM | ✅ whole-answer | ✅ facts-only |
| Conditional skip on hit | ✅ → writer | ✅ prefill retrieve |
| Judgment always fresh | N/A | ✅ analyze/safety |
| Parallel independent hops | optional | ✅ retrieve ∥ drug_check |
| Quality-gated seed | recommended | **required** |
| Retrieval backend | keyword OK for FX | **PrismRAG** for guidelines |
| Ledger on every run | ✅ `wrap()` | ✅ `wrap()` |

### Pattern selection guide

| Task shape | Use |
|------------|-----|
| Fixed pipeline, known roles | Graph nodes only |
| 1–N tool calls, order unknown | `Agent(pattern="react")` |
| Decomposable into explicit steps | `Agent(pattern="plan_solve")` |
| Draft must pass validator | `Agent(pattern="reflection")` or dedicated validator node |
| Repeat / paraphrase queries | `cache_gate` + correct `CacheProfile` |

---

## 15. Further reading

- [`docs/COMPOSE.md`](COMPOSE.md) — pluggable backends + `ChorusStack`
- [`docs/CACHE_PROFILES.md`](CACHE_PROFILES.md) — domain archetypes A–D
- [`docs/TERMINOLOGY.md`](TERMINOLOGY.md) — **ChorusGraph vs LangGraph boundaries**
- [`docs/FINANCE_MULTIAGENT_CHORUS.md`](FINANCE_MULTIAGENT_CHORUS.md) — FC2 topology
- [`docs/ENGINE_DESIGN_v0.1.md`](ENGINE_DESIGN_v0.1.md) — engine + agent patterns layer
- [`docs/DESIGN_v0.2.md`](DESIGN_v0.2.md) §7.5–7.8 — planning policy design
- [`benchmark/SCENARIOS.md`](../benchmark/SCENARIOS.md) — MVP matrix + profile table
- [`benchmark/results/mvp_scenarios/README.md`](../benchmark/results/mvp_scenarios/README.md) — archived runs
