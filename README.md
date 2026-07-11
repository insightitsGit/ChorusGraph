# ChorusGraph

[![CI](https://github.com/insightitsGit/ChorusGraph/actions/workflows/ci.yml/badge.svg)](https://github.com/insightitsGit/ChorusGraph/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.3-informational)](CHANGELOG.md)

**Native agent runtime with semantic cache, swappable retrieval (PrismRAG), auditable memory, and enterprise hardening — one pip install, five plug-in ports.**

```bash
pip install chorusgraph
chorusgraph-demo
```

**Interactive demo (Product Hunt / launch):** [insightitsGit.github.io/ChorusGraph/demo.html](https://insightitsGit.github.io/ChorusGraph/demo.html) — click-through walkthrough, no API key for steps 1–3.

> **ChorusGraph** = native engine + Prism stack · **LangGraph** = optional baseline for A/B comparison only ([`docs/TERMINOLOGY.md`](docs/TERMINOLOGY.md))

---

## What is ChorusGraph?

ChorusGraph is **not** a LangGraph wrapper. It ships a **native BSP graph engine** (`chorusgraph.core.Graph`) with the Prism product stack attached by default: semantic cache, L2 retrieval, L3 memory, Route Ledger, checkpoints, and observability.

You define nodes, edges, and conditional routing on the native engine. Cache, retrieval, memory, and tools plug in through explicit ports on `ChorusStack` — swap Redis, vector RAG, or custom tool registries without rewriting orchestration.

**ChorusGraph's own code has no LangGraph dependency on the product path.** The scheduler and all plug-in ports never import LangGraph. (Core dependency `prismlang` uses LangGraph internally for its own checkpointing utilities — it appears in `pip show`, but the ChorusGraph engine never calls it.) Install `chorusgraph[benchmark]` only when running FL*/HL* comparison scenarios.

---

## Why ChorusGraph?

Building production LLM agents usually means gluing six systems: orchestration, semantic cache, vector DB, reranker, checkpointing, and audit logs. ChorusGraph ships them as **one runtime** with explicit plug-in ports.

| Pain | ChorusGraph answer |
|------|-------------------|
| Repeat questions burn tokens | Two-stage semantic cache (coarse 64-d recall → full verify) |
| RAG is another integration project | `RetrievalBackend` plug-in — keyword default, PrismRAG vector opt-in |
| “Why did the agent say that?” | Route Ledger + `rule_chain` on every hop |
| Orchestration + ops duct tape | Native scheduler, health endpoints, Docker/k8s packaging |
| “Will this save us money?” | `chorusgraph-audit` — cold log simulation + pilot ledger reports |

---

## Quick Start (30 seconds)

```bash
pip install chorusgraph
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

```bash
chorusgraph-demo                              # routing + ledger (LLM-free)
chorusgraph-finance-patterns                # ReAct / Plan-Solve / Reflection (needs GEMINI_API_KEY)
chorusgraph-audit --log your_queries.jsonl    # simulated cache hit rate (no API key)
```

**Developer guide:** [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) — planning & reasoning, domain performance (finance vs healthcare), code examples.

Full install guide: [`docs/INSTALL.md`](docs/INSTALL.md) · AI IDE prompts: [`docs/AI_IDE_PROMPTS.md`](docs/AI_IDE_PROMPTS.md)

---

## Features

| Feature | Description |
|---------|-------------|
| **Native graph engine** | BSP scheduler, envelope channels, conditional routing — no LangGraph on product paths |
| **Semantic cache (L1)** | Two-stage gate: coarse recall → full verify; safe replay policies per domain |
| **Retrieval (L2)** | Keyword default; `PrismRAGRetrievalBackend` for vector + taxonomy (opt-in extra) |
| **Memory (L3)** | PrismCortex structured, replayable memory |
| **Route Ledger** | Per-hop audit trail: cache hits, scores, durations, `rule_chain` |
| **Checkpoints** | SQLite default; Postgres enterprise persistence (license-gated) |
| **Tool registry** | Allowlisted tools with sandbox; MCP-compatible patterns |
| **Resilience** | Timeouts, retries, circuit breakers, graceful node failure |
| **Observability** | Structured JSON logs, OpenTelemetry traces, health/metrics endpoints |
| **Multi-tenant guards** | Tenant isolation, resource limits, leakage tests |
| **Cold audit CLI** | `chorusgraph-audit` — estimate cache savings from query logs (no LLM calls) |
| **Agent patterns** | ReAct, Plan-Solve, Reflection via `chorusgraph.agents.Agent` — graph = plan |
| **Benchmark matrix** | 8 scenarios (FL/FC/HL/HC) with fairness disclosure |
| **Deploy packaging** | Dockerfile, docker-compose, k8s manifests |

---

## Comparison with LangGraph and DIY stacks

| | **LangGraph alone** | **DIY stack** (orchestrator + Redis + vector DB + reranker + logs) | **ChorusGraph** |
|--|---------------------|---------------------------------------------------------------------|-----------------|
| Orchestration | ✅ StateGraph | You integrate | ✅ Native `Graph` |
| Semantic cache | ❌ Roll your own | Separate service + glue | ✅ Built-in L1, swappable |
| Retrieval / RAG | ❌ External | Chroma/Pinecone + custom code | ✅ `RetrievalBackend` port |
| Audit / explainability | Limited | Custom logging | ✅ Route Ledger per hop |
| Safe cache replay | Your problem | Your problem | ✅ Domain profiles (e.g. facts-only in healthcare) |
| Benchmark proof | N/A | N/A | ✅ Published A/B vs LangGraph |
| LangGraph dependency | Required | Optional | **None on product path** |

ChorusGraph **includes** LangGraph baselines (`benchmark/fl*`, `benchmark/hl*`) for fair apples-to-apples comparison — same model, tools, prompts, workload. Native scenarios (`benchmark/fc*`, `benchmark/hc*`) compile with `chorusgraph.core.Graph` only.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Your graph — nodes, edges, conditional routing              │
├─────────────────────────────────────────────────────────────┤
│  ChorusStack — swappable ports                               │
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

Details: [`docs/COMPOSE.md`](docs/COMPOSE.md) · [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md)

---

## Plugin system

Four swappable ports on [`ChorusStack`](chorusgraph/compose/stack.py) — engine and scheduler stay fixed.

| Port | Default | Swap examples | Method |
|------|---------|---------------|--------|
| **Cache** (`CacheBackend`) | `PrismCacheBackend` | `RedisCacheBackend` | `with_cache()` |
| **Memory** (`MemoryBackend`) | `CortexMemoryBackend` | Disable with `enable_memory=False` | stack field |
| **Tools** (`ToolBackend`) | Finance tool registry | Custom `ToolRegistry`, MCP | `resolve_tools()` |
| **Retrieval** (`RetrievalBackend`) | `KeywordRetrievalBackend` | `PrismRAGRetrievalBackend` | `with_retrieval()` |
| **Persistence** (enterprise) | `SqlitePersistenceBackend` | `PostgresPersistenceBackend` | license-gated 5th port |

```python
from chorusgraph.compose import ChorusStack, PrismRAGRetrievalBackend, RedisCacheBackend
from chorusgraph.embedders import PrismlangOnnxEmbedder

backend = PrismRAGRetrievalBackend(
    embedder=PrismlangOnnxEmbedder(),
    mapping={"categories": [...], "rules": [...]},
)
backend.index(your_corpus)

stack = (
    ChorusStack.defaults(tenant_id="acme")
    .with_retrieval(backend)
    .with_cache(RedisCacheBackend(tenant_id="acme", redis_url="redis://localhost:6379/0"))
)
```

Full plug-in guide: [`docs/PLUGINS.md`](docs/PLUGINS.md)

---

## Prism ecosystem

| Layer | Component | Role |
|-------|-----------|------|
| L0 — hop | PrismLang | 64-d state compression + `rule_chain` audit |
| L1 — cache | PrismCache | Semantic gate, Resonance-scored recall |
| L2 — knowledge | Retrieval plug-in | Keyword default · vector + taxonomy opt-in |
| rerank | PrismResonance | Shared substrate rerank |
| L3 — memory | PrismCortex | Structured, replayable memory |
| transport | CHORUS / PrismAPI | Cross-node envelopes · federation hooks |

ChorusGraph is the **integration runtime** for the Prism family — PrismLang, PrismCache, PrismCortex, PrismRAG ship as defaults or opt-in extras, not separate science projects.

### Companion: PrismGuard (prompt-injection firewall)

[PrismGuard](https://pypi.org/project/prismguard/) ([0.1.4](https://pypi.org/project/prismguard/0.1.4/)) is a **separate package** — not a `ChorusStack` port. Install it alongside ChorusGraph when you want an auditable prompt-injection check before retrieve / LLM hops:

```bash
pip install chorusgraph "prismguard[prism,guard-model]==0.1.4"
prismguard-model download   # ~705 MB ONNX — not in the wheel; from GitHub Release v0.1.2
```

```python
from prismguard.integrations.chorusgraph import (
    create_checker_from_env,
    make_guard_handler,
    route_after_guard,
)

checker = create_checker_from_env()  # once per process
guard = make_guard_handler(checker)
# START → guard → [blocked → END | retrieve → …]
# Wire with Graph.add_node("guard", dict_node_adapter(guard, hop="guard"))
# Place guard before cache-gated hops so blocked prompts never seed cache
```

| Link | URL |
|------|-----|
| PyPI | https://pypi.org/project/prismguard/ · [0.1.4](https://pypi.org/project/prismguard/0.1.4/) |
| GitHub | https://github.com/insightitsGit/PrismGuard |
| Integration guide | https://github.com/insightitsGit/PrismGuard/blob/main/docs/integration-guide.md |
| ONNX model release | https://github.com/insightitsGit/PrismGuard/releases/tag/v0.1.2 |

See also [`docs/PLUGINS.md`](docs/PLUGINS.md#companion-prismguard).

---

## Benchmarks

Fair A/B vs competent LangGraph baselines — same model, tools, prompts, workload.

| Tier | Run ID | Tasks/scenario | Role |
|------|--------|----------------|------|
| **Mid (canonical)** | **`mid_20260708_111539`** | 100 | Primary regression + outreach proof |
| **Heavy (scale)** | **`heavy_20260708_140300`** | 300 | Scale validation + whitepaper / diligence |
| Smoke | `light_20260708_101409` | 40 | CI / quick regression |

**Start here:** [`docs/BENCHMARK_RESULTS.md`](docs/BENCHMARK_RESULTS.md) · archive index: [`benchmark/results/mvp_scenarios/README.md`](benchmark/results/mvp_scenarios/README.md) · machine pointer: [`benchmark/results/mvp_scenarios/latest.json`](benchmark/results/mvp_scenarios/latest.json)

Methodology: [`benchmark/FAIRNESS_H9.md`](benchmark/FAIRNESS_H9.md) · consolidated tables: [`benchmark/results/BENCHMARK_LATENCY_LLM_SUMMARY.md`](benchmark/results/BENCHMARK_LATENCY_LLM_SUMMARY.md)

July 2026 methodology fixes (benchmark-only — **no library release**): FL2 researcher prompt uses `annual_rate_pct` (matches tool schema); comparison script counts agent/tool errors in LangGraph success denominators. Supersedes pre-fix runs that inflated FL2 vs FC2. **Do not cite** invalid quota run `heavy_20260708_124337`.

### Task success (LangGraph → ChorusGraph) — mid tier, n=100

| Scenario | LangGraph | ChorusGraph | Delta |
|----------|-----------|-------------|-------|
| Finance single (FL1→FC1) | 87.0% | **98.0%** | +11.0 pp |
| Finance multi (FL2→FC2) | 87.0% | **94.0%** | +7.0 pp |
| Healthcare single (HL1→HC1) | 74.0% | **79.0%** | +5.0 pp |
| Healthcare multi (HL2→HC2) | 59.0% | **85.0%** | **+26 pp** |

### Task success — heavy tier, n=300

| Scenario | LangGraph | ChorusGraph | Delta |
|----------|-----------|-------------|-------|
| Finance single (FL1→FC1) | 90.0% | **96.7%** | +6.7 pp |
| Finance multi (FL2→FC2) | 89.0% | **93.0%** | +4.0 pp |
| Healthcare single (HL1→HC1) | 73.7% | **84.0%** | +10.3 pp |
| Healthcare multi (HL2→HC2) | 62.3% | **77.3%** | **+15 pp** |

### LLM calls and latency (mid tier, mean per task)

| Scenario | LLM calls (L → C) | Mean latency ms (L → C) | Cache hit (C) |
|----------|-------------------|-------------------------|---------------|
| FL1 / FC1 | 3.24 → **0.77** (−76%) | 4760 → **1348** (−72%) | 52% |
| FL2 / FC2 | 2.03 → **0.69** (−66%) | 3269 → **1085** (−67%) | 40% |
| HL1 / HC1 | 3.00 → **1.56** (−48%) | 7036 → **3990** (−43%) | 60% |
| HL2 / HC2 | 3.82 → **3.15** (−18%) | 10296 → 10753 (tie) | 51% |

### LLM calls and latency (heavy tier, mean per task)

| Scenario | LLM calls (L → C) | Mean latency ms (L → C) | Cache hit (C) |
|----------|-------------------|-------------------------|---------------|
| FL1 / FC1 | 3.33 → **0.80** (−76%) | 4972 → **1318** (−73%) | 49.7% |
| FL2 / FC2 | 2.04 → **0.75** (−63%) | 3081 → **1335** (−57%) | 34.7% |
| HL1 / HC1 | 2.94 → **1.33** (−55%) | 7105 → **3812** (−46%) | 72.7% |
| HL2 / HC2 | 3.85 → **2.67** (−31%) | 10354 → **9537** (−8%; p95 tie) | 79.0% |

Healthcare multi saves fewer LLM calls by design (facts-only cache, judgment hops re-run). Lead with accuracy (+26 pp mid / +15 pp heavy), not cost; disclose HC2 p95 wall-clock tie.

### Full reports and raw data (reproducible artifacts)

Each run ships a human report, run metadata, and a tarball of per-task JSONL traces.

| Tier | Comparison report | Raw results (`results.tar.gz`) | Run metadata |
|------|-------------------|-------------------------------|--------------|
| Light (40) | [`light_20260708_101409/COMPARISON_REPORT.md`](benchmark/results/azure_light_20260708_101409/mvp_scenarios/light_20260708_101409/COMPARISON_REPORT.md) | [`results.tar.gz`](benchmark/results/azure_light_20260708_101409/mvp_scenarios/light_20260708_101409/results.tar.gz) | [`run_meta.json`](benchmark/results/azure_light_20260708_101409/mvp_scenarios/light_20260708_101409/run_meta.json) |
| **Mid (100)** | [`mid_20260708_111539/COMPARISON_REPORT.md`](benchmark/results/azure_mid_20260708_111539/mvp_scenarios/mid_20260708_111539/COMPARISON_REPORT.md) | [`results.tar.gz`](benchmark/results/azure_mid_20260708_111539/mvp_scenarios/mid_20260708_111539/results.tar.gz) | [`run_meta.json`](benchmark/results/azure_mid_20260708_111539/mvp_scenarios/mid_20260708_111539/run_meta.json) |
| **Heavy (300)** | [`heavy_20260708_140300/COMPARISON_REPORT.md`](benchmark/results/azure_heavy_20260708_140300/mvp_scenarios/heavy_20260708_140300/COMPARISON_REPORT.md) | [`results.tar.gz`](benchmark/results/azure_heavy_20260708_140300/mvp_scenarios/heavy_20260708_140300/results.tar.gz) | [`run_meta.json`](benchmark/results/azure_heavy_20260708_140300/mvp_scenarios/heavy_20260708_140300/run_meta.json) |

Extract raw traces: `tar -xzf results.tar.gz` — contains per-scenario `*.jsonl` and `comparison.json`.

```bash
pip install -e ".[benchmark,gemini]"
python -m benchmark.run_scenarios --tier light --scenarios all   # needs GEMINI_API_KEY
chorusgraph-audit --log tests/fixtures/audit_cold_queries.jsonl  # no API key
```

---

## Enterprise features

| Capability | Status |
|------------|--------|
| Native engine (no LangGraph on product path) | ✅ |
| CI — 329+ tests, deterministic tier (no live keys) | ✅ |
| Resilience, security, observability | ✅ |
| Docker / k8s deploy | ✅ [`docs/DEPLOY.md`](docs/DEPLOY.md) |
| Frozen public API 1.0 | ✅ [`docs/API_1_0.md`](docs/API_1_0.md) |
| SQLite durable graph (free tier) | ✅ |
| Postgres persistence + enterprise license | ✅ license-gated |
| External security audit / production SLO soak | 🟡 Phase 2 |

Readiness scorecard: [`docs/ENTERPRISE_READINESS.md`](docs/ENTERPRISE_READINESS.md) · threat model: [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md)

---

## Documentation

| Doc | Description |
|-----|-------------|
| [`docs/INSTALL.md`](docs/INSTALL.md) | pip extras, PrismRAG walkthrough, audit CLI |
| [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) | Build agents on native `Graph` |
| [`docs/PLUGINS.md`](docs/PLUGINS.md) | Cache, memory, tools, retrieval ports |
| [`docs/COMPOSE.md`](docs/COMPOSE.md) | `ChorusStack` composition patterns |
| [`docs/WHITEPAPER.md`](docs/WHITEPAPER.md) | Product thesis + technical depth |
| [`docs/BENCHMARK.md`](docs/BENCHMARK.md) | Fairness methodology |
| [`docs/BENCHMARK_RESULTS.md`](docs/BENCHMARK_RESULTS.md) | Published A/B results (mid + heavy) + artifact links |
| [`docs/CACHE_PROFILES.md`](docs/CACHE_PROFILES.md) | Safe replay policies by domain |
| [`docs/STABILITY.md`](docs/STABILITY.md) | 1.0 API stability guarantee |
| [`docs/TERMINOLOGY.md`](docs/TERMINOLOGY.md) | ChorusGraph vs LangGraph naming policy |
| [`benchmark/SCENARIOS.md`](benchmark/SCENARIOS.md) | FL/FC/HL/HC scenario matrix |
| [`docs/AI_IDE_PROMPTS.md`](docs/AI_IDE_PROMPTS.md) | Cursor / Copilot install & migration prompts |

---

## Examples

- [Local RAG with Chroma + ChorusGraph](chorusgraph/examples/chroma_local_rag/) -- offline vector RAG with native retrieve-to-answer graph

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

Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md) · workflow: [`docs/WORKFLOW.md`](docs/WORKFLOW.md) · process: [`docs/PROCESS.md`](docs/PROCESS.md)

---

## Extras

| Extra | Purpose |
|-------|---------|
| `retrieval` | Chroma + `PrismRAGRetrievalBackend` |
| `gemini` | Live Gemini examples |
| `cortex` | PrismCortex L3 memory |
| `benchmark` | LangGraph baselines (FL/HL) + chromadb |
| `benchmark-healthcare` | Healthcare benchmark scenarios (HC1/HC2) |
| `postgres` | Postgres DSN paths in deploy docs |
| `postgres-checkpoint` | LangGraph Postgres checkpointer (optional) |
| `langgraph` | Baselines / compat tests — **not** required for core product |
| `dev` | pytest, ruff, mypy, coverage |
| `enterprise-ci` | Full CI matrix locally |

Lockfile: `requirements-lock.txt` · release notes: [`CHANGELOG.md`](CHANGELOG.md) · [`docs/RELEASE.md`](docs/RELEASE.md)

---

## Roadmap

**Shipped in 1.0:** native engine, semantic cache, retrieval plug-in, Route Ledger, SQLite persistence, benchmarks, deploy packaging, frozen public API.

**Phase 2 (documented, in progress):**

| Item | Status |
|------|--------|
| Postgres-native Cortex GraphStore | 🟡 SQLite ships today |
| Ledger token fields for live dollar reporting in `chorusgraph-audit --ledger` | 🟡 schema sign-off pending |
| CHORUS cipher external audit | TLS default; cipher opt-in |
| Production Azure soak SLO sign-off | harness shipped |
| External penetration test certification | pre-regulated-customer |
| Prebuilt agent nodes (ReAct / supervisor) | roadmap primitive |

Details: [`docs/WHITEPAPER.md`](docs/WHITEPAPER.md) §9 · [`docs/ENTERPRISE_READINESS.md`](docs/ENTERPRISE_READINESS.md)

---

## License

Apache-2.0 — see [LICENSE](LICENSE).

## Community

| | |
|---|---|
| [Contributing](CONTRIBUTING.md) | Dev setup, PR checklist, FC/HC vs FL/HL rules |
| [Code of conduct](CODE_OF_CONDUCT.md) | Contributor Covenant |
| [Security policy](SECURITY.md) | Private vulnerability reporting |

Built by [Insight IT Solutions](https://github.com/insightitsGit). Dogfooded in production agent hubs. Part of the Prism family (PrismLang, PrismCache, PrismCortex, PrismRAG, [PrismGuard 0.1.4](https://pypi.org/project/prismguard/0.1.4/)).

**Questions / enterprise:** open a [GitHub issue](https://github.com/insightitsGit/ChorusGraph/issues) or see [`docs/WHITEPAPER.md`](docs/WHITEPAPER.md) for commercial framing.
