# ChorusGraph

[![CI](https://github.com/insightitsGit/ChorusGraph/actions/workflows/ci.yml/badge.svg)](https://github.com/insightitsGit/ChorusGraph/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-informational)](CHANGELOG.md)

**Native agent runtime with semantic cache, swappable retrieval (PrismRAG), auditable memory, and enterprise hardening — one pip install, four plug-in ports.**

ChorusGraph is **not** a LangGraph wrapper. It ships a **native BSP graph engine** (`chorusgraph.core.Graph`) with the Prism stack attached by default: semantic cache, L2 retrieval, L3 memory, Route Ledger, checkpoints, and observability. Swap backends (Redis cache, vector RAG, custom tools) without rewriting orchestration.

> **ChorusGraph** = native engine + product stack · **LangGraph** = optional baseline for A/B comparison only ([`docs/TERMINOLOGY.md`](docs/TERMINOLOGY.md))

---

## Why ChorusGraph

Building production LLM agents usually means gluing six systems: orchestration, semantic cache, vector DB, reranker, checkpointing, and audit logs. ChorusGraph ships them as **one runtime** with explicit plug-in ports.

| Pain | ChorusGraph answer |
|------|-------------------|
| Repeat questions burn tokens | Two-stage semantic cache (coarse 64-d recall → full verify) |
| RAG is another integration project | `RetrievalBackend` plug-in — keyword default, PrismRAG vector opt-in |
| “Why did the agent say that?” | Route Ledger + `rule_chain` on every hop |
| Orchestration + ops duct tape | Native scheduler, health endpoints, Docker/k8s packaging |

**Core install has no LangGraph dependency.** Baselines that compare against LangGraph use the optional `[benchmark]` extra.

---

## Quick start

```bash
pip install chorusgraph
# Optional: vector retrieval (Chroma + PrismRAG plug-in)
pip install "chorusgraph[retrieval]"
```

```python
from chorusgraph import Graph, START, END, ChorusStack
from chorusgraph.core.node import dict_node_adapter

stack = ChorusStack.defaults(tenant_id="demo")

g = Graph(tenant_id="demo", graph_id="hello")
g.add_node(
    "echo",
    dict_node_adapter(lambda s: {"reply": f"Hello, {s.get('name', 'world')}"}, hop="echo"),
)
g.add_edge(START, "echo")
g.add_edge("echo", END)

out = g.compile(stack=stack).invoke({"name": "ChorusGraph"})
print(out)  # {'reply': 'Hello, ChorusGraph'}
```

Run the bundled demo:

```bash
chorusgraph-demo
```

Full install guide (extras, PrismRAG walkthrough): [`docs/INSTALL.md`](docs/INSTALL.md)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Your graph — nodes, edges, conditional routing              │
├─────────────────────────────────────────────────────────────┤
│  ChorusStack — four swappable ports                          │
│  ┌──────────┬──────────┬──────────┬──────────────────────┐  │
│  │ Cache    │ Memory   │ Tools    │ Retrieval (L2)       │  │
│  │ Prism /  │ Cortex   │ Registry │ Keyword / PrismRAG   │  │
│  │ Redis    │          │          │                      │  │
│  └──────────┴──────────┴──────────┴──────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Engine (fixed): BSP scheduler · envelopes · Resonance · JL  │
├─────────────────────────────────────────────────────────────┤
│  Route Ledger · checkpoints · tenant guards · observability  │
└─────────────────────────────────────────────────────────────┘
```

| Layer | Default | Swap |
|-------|---------|------|
| **L1 cache** | Semantic PrismCache | `RedisCacheBackend` |
| **L2 retrieval** | Keyword overlap | `PrismRAGRetrievalBackend` |
| **L3 memory** | PrismCortex | Disable or custom |
| **Tools** | Finance registry | MCP / allowlisted registry |

Details: [`docs/COMPOSE.md`](docs/COMPOSE.md) · [`docs/PLUGINS.md`](docs/PLUGINS.md)

### PrismRAG retrieval plug-in

```python
from chorusgraph.compose import ChorusStack, PrismRAGRetrievalBackend
from chorusgraph.embedders import PrismlangOnnxEmbedder

backend = PrismRAGRetrievalBackend(
    embedder=PrismlangOnnxEmbedder(),
    mapping={"categories": [...], "rules": [...]},
)
backend.index(your_corpus)

stack = ChorusStack.defaults(tenant_id="acme").with_retrieval(backend)
retrieve_node = stack.to_retrieve_handler(topic="policy", top_k=6)
```

---

## Prism stack layers

| Layer | Component | Role |
|-------|-----------|------|
| L0 — hop | PrismLang | 64-d state compression + `rule_chain` audit |
| L1 — cache | PrismCache | Semantic gate, Resonance-scored recall |
| L2 — knowledge | Retrieval plug-in | Keyword default · vector + taxonomy opt-in |
| rerank | PrismResonance | Shared substrate rerank |
| L3 — memory | PrismCortex | Structured, replayable memory |
| transport | CHORUS / PrismAPI | Cross-node envelopes · federation hooks |

---

## Benchmark proof (Azure, canonical run `20260704_212111`)

Fair A/B vs competent LangGraph baselines — same model, tools, prompts, workload. See [`benchmark/FAIRNESS_H9.md`](benchmark/FAIRNESS_H9.md).

| Scenario | LangGraph | ChorusGraph | Delta |
|----------|-----------|-------------|-------|
| Finance single (FL1→FC1) | 87.5% | **100%** | +12.5 pp |
| Finance multi (FL2→FC2) | 75% | **87.5%** | +12.5 pp |
| Healthcare single (HL1→HC1) | 72.5% | 72.5% | tie |
| Healthcare multi (HL2→HC2) | 57.5% | **87.5%** | **+30 pp** |

Full report: [`benchmark/results/azure_20260704_212111/.../COMPARISON_REPORT.md`](benchmark/results/azure_20260704_212111/mvp_scenarios/20260704_212111/20260704_212111/COMPARISON_REPORT.md)

Run scenarios locally (requires `GEMINI_API_KEY` + `[benchmark]` extra):

```bash
pip install -e ".[benchmark,gemini]"
python -m benchmark.run_scenarios --tier light --scenarios all
```

---

## Enterprise 1.0

| Capability | Status |
|------------|--------|
| Native engine (no LangGraph on product path) | ✅ |
| CI — 327+ tests, no live keys required | ✅ |
| Resilience, security, observability | ✅ |
| Docker / k8s deploy | ✅ [`docs/DEPLOY.md`](docs/DEPLOY.md) |
| Frozen public API | ✅ [`docs/API_1_0.md`](docs/API_1_0.md) |
| SQLite durable graph (Postgres Phase 2) | 🟡 |

Readiness scorecard: [`docs/ENTERPRISE_READINESS.md`](docs/ENTERPRISE_READINESS.md)

---

## Documentation

| Doc | Description |
|-----|-------------|
| [`docs/INSTALL.md`](docs/INSTALL.md) | pip extras, PrismRAG implementation guide |
| [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) | Build agents on native `Graph` |
| [`docs/PLUGINS.md`](docs/PLUGINS.md) | Cache, memory, tools, retrieval ports |
| [`docs/WHITEPAPER.md`](docs/WHITEPAPER.md) | Product thesis + technical depth |
| [`docs/BENCHMARK.md`](docs/BENCHMARK.md) | Fairness methodology |
| [`docs/STABILITY.md`](docs/STABILITY.md) | 1.0 API stability guarantee |
| [`benchmark/SCENARIOS.md`](benchmark/SCENARIOS.md) | FL/FC/HL/HC scenario matrix |

---

## Development

```bash
git clone https://github.com/insightitsGit/ChorusGraph.git
cd ChorusGraph
pip install -e ".[dev,benchmark,gemini,retrieval]"
pytest                    # deterministic tier — no API keys
pytest -m live            # live Gemini (needs GEMINI_API_KEY)
ruff check tests .github
```

---

## Optional dependencies

| Extra | Purpose |
|-------|---------|
| `retrieval` | Chroma + `PrismRAGRetrievalBackend` |
| `gemini` | Live Gemini examples |
| `cortex` | PrismCortex L3 memory |
| `benchmark` | LangGraph baselines (FL/HL) + chromadb |
| `dev` | pytest, ruff, mypy, coverage |

---

## Principles

- **Native first** — FC/HC product paths use `chorusgraph.core.Graph` only
- **Safe cache before fast cache** — two-stage verify; no unsafe generative replay
- **Measure, don't assert** — publish benchmarks with fairness disclosure
- **Batteries included, batteries swappable** — defaults work; ports swap cleanly

---

## License

Apache-2.0 — see [LICENSE](LICENSE).

---

## Provenance

Built by [Insight IT Solutions](https://github.com/insightitsGit). Dogfooded in production agent hubs. Part of the Prism family (PrismLang, PrismCache, PrismCortex, PrismRAG).

**Questions / enterprise:** open a GitHub issue or see [`docs/WHITEPAPER.md`](docs/WHITEPAPER.md) for commercial framing.
