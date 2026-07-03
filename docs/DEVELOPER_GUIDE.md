# ChorusGraph Developer Guide

> **Terminology:** **ChorusGraph** = native engine + full product stack. **Not LangGraph.** See [`TERMINOLOGY.md`](TERMINOLOGY.md).
>
> **Composition:** [`COMPOSE.md`](COMPOSE.md) — `ChorusStack` attaches Prism defaults; swap cache, memory, checkpoint, ledger, or tools per port.

Standard patterns for building agents on **`chorusgraph.core.Graph`**.

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

Finance and healthcare benchmarks use the same pattern:

1. **`cache_gate` node** — `chorusgraph.cache_gate.gate()` lookup
2. **On hit** — restore payload, route to writer (skip LLM hops)
3. **On miss** — run agent loop, **seed cache** after success

```python
from chorusgraph.cache_gate import gate
from chorusgraph.sections.models import CachePolicy, Section

decision = gate(
    query_text,
    Section(section_id="...", category_slug="fx_rates", content=query_text, cache_policy=CachePolicy.REPLAY_SAFE),
    runtime.cache,
    runtime.sidecar,
    coarse_threshold=0.80,
    verify_threshold=0.85,
)
```

**FC1 / FC2** use this — that is why finance C-scenarios show ~3–4× latency wins. **HC1 / HC2** use clinical cache with `pipeline_depth` in the key.

Without cache, C vs L latency differs only by engine overhead (~1–5%) because **Gemini dominates**.

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

## 10. Further reading

- [`docs/COMPOSE.md`](COMPOSE.md) — pluggable backends + `ChorusStack`
- [`docs/TERMINOLOGY.md`](TERMINOLOGY.md) — **ChorusGraph vs LangGraph boundaries**
- [`docs/ENGINE_DESIGN_v0.1.md`](ENGINE_DESIGN_v0.1.md) — engine architecture
- [`benchmark/SCENARIOS.md`](../benchmark/SCENARIOS.md) — MVP matrix
- [`benchmark/results/mvp_scenarios/README.md`](../benchmark/results/mvp_scenarios/README.md) — archived runs
