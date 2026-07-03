# ADR-004: Native Graph Runtime

**Status:** Accepted · implemented in `chorusgraph/core/` (handoff H20+, 2026-07-02)  
**Supersedes:** DESIGN v0.2 §5 “adapter-first only” as the *sole* execution path  
**Date:** 2026-07-02

> **Terminology:** **ChorusGraph** = native engine below. LangGraph is **not** ChorusGraph — only for FL*/HL* baselines and legacy `wrap()`. See [`TERMINOLOGY.md`](TERMINOLOGY.md).

> **Note:** The phase-1 packages `chorusgraph/graph/`, `chorusgraph/runtime/`, and
> `chorusgraph/engine/` were removed in H20. Use `chorusgraph.core.Graph` — envelope channels,
> Resonance bus routing, BSP scheduler, and native checkpointing. LangGraph remains available
> via `wrap()` for migration benchmarks only (FL*, HL*).

## Context

ChorusGraph was initially shipped as a LangGraph adapter (`wrap()` + Prism hooks). The product
design (DESIGN v0.2 §4–§5) describes a full runtime — graph compiler, scheduler, built-in nodes.
Benchmark **ChorusGraph scenarios (FC*, HC*)** must compile native `Graph` graphs; LangGraph is
reserved for **baseline scenarios (FL*, HL*)** only.

## Decision

Introduce a **native execution engine** as the primary path for new ChorusGraph graphs:

| Layer | Package | Responsibility |
|-------|---------|----------------|
| Builder | `chorusgraph/graph/` | `Graph`, `add_node`, `add_edge`, `add_conditional_edges`, `compile()` |
| IR | `chorusgraph/graph/ir.py` | Lowered node/edge/router representation |
| Scheduler | `chorusgraph/runtime/compiled.py` | Super-step loop: run node → merge state → route |
| State | `chorusgraph/runtime/state.py` | List-append merge for `rule_chain`, `prism_sequence`, etc. |

LangGraph remains supported via `wrap()` for **migration** (existing hubs, benchmark baselines A/C/E).

## API (Phase 1)

```python
from chorusgraph.graph import Graph
from chorusgraph.runtime.constants import END, START

g = Graph(MyState)
g.add_node("analyze", analyze_fn)
g.add_edge(START, "analyze")
g.add_conditional_edges("route", router_fn, {"a": "node_a", "b": "node_b"})
g.add_edge("node_a", END)
compiled = g.compile()
result = compiled.invoke(initial_state)
```

`CompiledGraph` implements:

- `invoke` / `ainvoke`
- `stream(..., stream_mode="debug")` — LangGraph-compatible debug events for Route Ledger
- `_native = True` marker

Node contract: `(state: dict) -> dict` partial update. No LangGraph import required.

## Migration order

1. ✅ Demo graph (`chorusgraph/examples/demo_graph.py`)
2. ✅ Finance agent graphs (`patterns_graph.py` — FC1 native; `graph.py` legacy demo only)
3. ✅ Benchmark Chorus scenarios (FC1, FC2, HC1, HC2) — **no LangGraph**
4. LangGraph import adapter (optional `Graph.from_langgraph()` — not yet built)

Baselines FL1, FL2, HL1, HL2 stay on LangGraph intentionally (fair comparison).

Enforcement: `tests/test_fc_hc_no_langgraph.py` + [`TERMINOLOGY.md`](TERMINOLOGY.md).

## Still missing (Phase 2+)

See **DESIGN_v0.3_PRISM_ENGINE.md** for full Prism-family mapping (PrismLang, CHORUS,
PrismAPI, Resonance, RAG, Cortex, Mesh).

| Capability | Target phase |
|------------|--------------|
| Parallel fan-out / join | Phase 2 |
| Native checkpointer (section snapshots) | Phase 2 |
| `interrupt` / HITL resume | Phase 3 |
| Token/state streaming API | Phase 3 |
| `Graph.from_langgraph()` import | Phase 2 |
| Subgraph composition | Phase 2 |
| Built-in node kinds wired to scheduler (`tool`, `llm`, `cache_gate`) | Phase 2 |
| MCP client tool surface | Phase 3 |

## Consequences

- **ChorusGraph paths (FC*, HC*, product graphs)** use `chorusgraph.core.Graph` — never `langgraph.StateGraph`.
- **LangGraph baselines (FL*, HL*)** use `StateGraph` for paired comparison only.
- `pyproject.toml` keeps `langgraph` as optional dependency for baselines + checkpoint compat.
- Route Ledger adapter works unchanged — native engine emits the same debug stream shape.

## Verification

- `tests/test_native_runtime.py` — unit tests
- `tests/test_adapter.py` — demo graph e2e via `wrap()` (proves ledger parity)
