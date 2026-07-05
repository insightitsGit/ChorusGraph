# ChorusGraph — Terminology & Framework Boundaries

**Status:** Active policy · read before writing or migrating benchmark/product code  
**Last updated:** 2026-07-03

---

## The rule (non‑negotiable)

When this repo, docs, or a stakeholder says **“ChorusGraph”**, they mean the **full native product**:

| Layer | Package / module | Required on ChorusGraph paths |
|-------|------------------|-------------------------------|
| Graph builder | `chorusgraph.core.Graph` | Yes |
| Scheduler / BSP | `chorusgraph.core.scheduler` | Yes |
| Channel state | `chorusgraph.core.channels` | Yes |
| Envelopes | `PrismEnvelope` via `ctx.publish()` | Yes |
| Semantic cache | `chorusgraph.cache_gate` | When scenario uses cache |
| Route ledger | `chorusgraph.adapter.wrap()` | When auditing is required |
| Checkpoints | `chorusgraph.core.persistence` / checkpoint package | When durability is required |
| Prism stack | PrismCache, PrismLang, Cortex, RAG, etc. | As scenario requires |

**Do not use LangGraph** (`langgraph`, `StateGraph`, `langgraph.graph`) on any path labeled ChorusGraph — in code, tests, examples tied to benchmarks, or new product graphs.

LangGraph is **only** for **baseline comparison scenarios** (FL*, HL*) and legacy hub migration via `wrap()`. It is **not** part of the ChorusGraph product surface.

---

## Naming in benchmarks

| Prefix | Meaning | Orchestration |
|--------|---------|---------------|
| **FC*** | Finance · **ChorusGraph** | `chorusgraph.core.Graph` only |
| **HC*** | Healthcare · **ChorusGraph** | `chorusgraph.core.Graph` only |
| **FL*** | Finance · **LangGraph baseline** | `langgraph.graph.StateGraph` |
| **HL*** | Healthcare · **LangGraph baseline** | `langgraph.graph.StateGraph` |

Legacy containers A–F map to this matrix (A→FL1, B→FC1, C→HL2, D→HC2, E→FL2, F→FC2).

### Allowed paths

| Path | Framework |
|------|-----------|
| `benchmark/fc1/`, `benchmark/fc2/` | Native ChorusGraph |
| `benchmark/hc1/`, `benchmark/hc2/` | Native ChorusGraph |
| `chorusgraph/examples/finance_agent/patterns_graph.py` | Native (FC1 graph) |
| `benchmark/fl1/`, `benchmark/fl2/` | LangGraph baseline |
| `benchmark/hl1/`, `benchmark/hl2/` | LangGraph baseline |

### Forbidden

- Importing `langgraph` in any file under `benchmark/fc*`, `benchmark/hc*`, or FC1 graph builders.
- Building new “ChorusGraph” features on `StateGraph` “for speed” or “for compatibility”.
- Describing a hybrid (LangGraph orchestration + Prism hooks) as “ChorusGraph” in docs or reports.

---

## What LangGraph is still for

1. **Fair baselines** — FL1, FL2, HL1, HL2 so paired reports can say “ChorusGraph vs LangGraph” with only orchestration differing.
2. **Legacy migration** — existing hubs that still compile `StateGraph`; run through `chorusgraph.adapter.wrap()` until rewritten to native `Graph`.
3. **Optional dependency** — `pip install "chorusgraph[langgraph]"` or `[benchmark]` for FL*/HL* baselines only; **not** required for FC/HC or the core library.

Demo-only code uses native `chorusgraph.core.Graph` (e.g. `patterns_graph.py`, `graph.py`). **Must not** be wired into FC/HC benchmark runners with LangGraph.

---

## Enforcement

| Mechanism | Location |
|-----------|----------|
| AST import guard | `tests/test_fc_hc_no_langgraph.py` |
| Developer patterns | `docs/DEVELOPER_GUIDE.md` |
| Scenario matrix | `benchmark/SCENARIOS.md` |
| Agent / IDE rule | `.cursor/rules/chorusgraph-native.mdc` |

If a change adds `langgraph` to an FC/HC path, **the PR is wrong** — migrate to `chorusgraph.core.Graph` or move the code to an FL/HL baseline.

---

## Quick decision tree

```
Building or changing agent orchestration?
│
├─ Benchmark or product path labeled FC* or HC*?
│  └─ YES → chorusgraph.core.Graph ONLY
│
├─ Explicit LangGraph baseline (FL* / HL*)?
│  └─ YES → langgraph.graph.StateGraph
│
├─ Legacy hub not yet migrated?
│  └─ wrap(StateGraph) for ledger/cache; plan native Graph migration
│
└─ Docs or conversation say "ChorusGraph"?
   └─ Assume native engine + full Prism stack — never LangGraph
```

---

## Related docs

- [`COMPOSE.md`](COMPOSE.md) — **pluggable section backends + `ChorusStack` defaults**
- [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) — how to build on native `Graph`
- [`ADR-004-native-runtime.md`](ADR-004-native-runtime.md) — runtime decision record
- [`DESIGN_v0.3_PRISM_ENGINE.md`](DESIGN_v0.3_PRISM_ENGINE.md) — engine architecture
- [`benchmark/SCENARIOS.md`](../benchmark/SCENARIOS.md) — runnable scenario matrix
