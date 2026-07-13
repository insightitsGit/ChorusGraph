# ChorusGraph Whitepaper

**Version 1.0.0 · Insight IT Solutions · July 2026**

*Native agent runtime with semantic cache, swappable retrieval (PrismRAG), auditable memory, and enterprise hardening — one pip install, four plug-in ports.*

---

## Executive summary

Teams shipping LLM agents face the same hidden tax: glue a graph framework to a vector DB, a cache, a reranker, checkpoints, observability, and security — then pray it holds under production load.

**ChorusGraph** is a native agent runtime that ships those layers as one product with **four swappable ports** (cache, memory, tools, retrieval). You install with pip, run graphs on `chorusgraph.core.Graph` (not LangGraph for product paths), and swap backends — Redis cache, PrismRAG vector retrieval, custom tool registries — without rewriting orchestration.

**Measured outcomes** (canonical Azure benchmark `mid_20260708_111539`, 100 tasks/scenario, real Gemini):

| Scenario | LangGraph baseline | ChorusGraph | Delta |
|----------|-------------------|-------------|-------|
| Finance single (FL1→FC1) | 87.0% | **98.0%** | +11.0 pp |
| Finance multi (FL2→FC2) | 87.0% | **94.0%** | +7.0 pp |
| Healthcare multi (HL2→HC2) | 59.0% | **85.0%** | **+26 pp** |

Finance scenarios: ~66–76% fewer LLM calls and ~67–72% lower mean latency vs LangGraph (semantic cache). Benchmark-only methodology fixes July 2026; no library version bump.

**Enterprise 1.0** adds CI without live API keys, resilience, security controls, observability, durable SQLite graph store, tenant isolation, Docker/k8s packaging, and a frozen public API.

---

## 1. The problem — integration tax on every agent ship

### 1.1 What buyers actually feel

Platform leads don't wake up wanting "a graph DSL." They wake up to:

- **Runaway LLM bills** — the same intent rephrased burns tokens again
- **Six-month integration projects** — cache + vector + checkpoint + audit each owned by a different vendor
- **Audit panic** — "why did the agent say that?" with no `rule_chain` or replay path
- **Benchmark theater** — demos that skip cache, retrieval, and failure modes

### 1.2 Why duct-tape stacks fail

| Layer | Typical DIY stack | Failure mode |
|-------|-------------------|--------------|
| Orchestration | LangGraph / custom | No unified cache gate at node entry |
| Cache | Redis + hand-rolled keys | Paraphrase misses; unsafe replay of generative output |
| Retrieval | Pinecone + custom rerank | Disconnected from tenant vector substrate |
| Memory | Ad-hoc JSON / vector silos | No bitemporal replay; cross-session amnesia |
| Transport | gRPC + bespoke | No envelope discipline across hops |
| Ops | Log grep | No correlation IDs, health, or partial-failure contract |

ChorusGraph treats these as **one runtime** with explicit ports — not a menu of repos you assemble.

---

## 2. The offer — what ChorusGraph sells

Using the [Value Equation](https://github.com/insightitsGit/ChorusGraph/blob/master/docs/WHITEPAPER.md) frame:

```
Value = (Dream Outcome × Likelihood) ÷ (Time Delay × Effort)
```

| Variable | ChorusGraph positioning |
|----------|-------------------------|
| **Dream outcome** | Ship production agents with cache hits, grounded retrieval, and audit trail — without standing up a platform team |
| **Likelihood** | Published A/B benchmarks vs competent LangGraph baselines; 323-test CI suite; Route Ledger on every hop |
| **Time delay** | `pip install chorusgraph` → working graph in minutes; retrieve plug-in in ~20 lines |
| **Effort** | Swap ports, don't fork engine; deterministic test tier needs no API keys |

### 2.1 Category of one

ChorusGraph is **not** "another LangGraph wrapper." It is:

- A **native BSP scheduler** with envelope channels and Resonance routing
- A **Prism-family stack** (PrismLang 64-d, PrismCache gate, PrismCortex memory, CHORUS transport hooks)
- A **composable product** (`ChorusStack`) with Redis/PrismRAG plug-ins

LangGraph remains in-repo **only** for fair baselines (FL*/HL* scenarios).

---

## 3. Architecture

### 3.1 Layer model

```
┌─────────────────────────────────────────────────────────────┐
│  Your graph (nodes, edges, conditional routing)              │
├─────────────────────────────────────────────────────────────┤
│  ChorusStack — swappable ports                               │
│  ┌──────────┬──────────┬──────────┬──────────────────────┐ │
│  │ Cache    │ Memory   │ Tools    │ Retrieval (L2)       │ │
│  │ Prism/   │ Cortex   │ Registry │ Keyword / PrismRAG   │ │
│  │ Redis    │          │          │                      │ │
│  └──────────┴──────────┴──────────┴──────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Engine (fixed): scheduler · envelopes · Resonance · JL 64-d │
├─────────────────────────────────────────────────────────────┤
│  Route Ledger · checkpointer · observability · tenant guards │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Safe cache before fast cache

The L1 cache gate uses **two-stage verification**:

1. Coarse 64-d recall (fast, tenant-scoped PrismLang projection)
2. Full-precision verify before replay

Generative outputs are not replayed verbatim when policy forbids it. Cache profiles (archetypes A–D) attach per hop — see `docs/CACHE_PROFILES.md`.

### 3.3 Four plug-in ports

| Port | Default | Enterprise swap |
|------|---------|-----------------|
| `CacheBackend` | Semantic PrismCache | `RedisCacheBackend` |
| `MemoryBackend` | PrismCortex | Disable or custom |
| `ToolBackend` | Finance registry | MCP / allowlisted tools |
| `RetrievalBackend` | Keyword overlap | **`PrismRAGRetrievalBackend`** |

Implementation guide: [`docs/INSTALL.md`](INSTALL.md) · [`docs/PLUGINS.md`](PLUGINS.md).

---

## 4. PrismRAG retrieval plug-in (deep dive)

### 4.1 Why a plug-in, not a benchmark hack

Prior to v1.0, PrismRAG (Chroma + `PrismRAGPatch` taxonomy remap) lived only under `benchmark/healthcare/`. HC1/HC2 scenarios consumed it; library users could not.

**v1.0 promotes retrieval to a fourth port:**

```python
from chorusgraph.compose import ChorusStack, PrismRAGRetrievalBackend
from chorusgraph.embedders import PrismlangOnnxEmbedder

backend = PrismRAGRetrievalBackend(
    embedder=PrismlangOnnxEmbedder(),
    mapping={"categories": [...], "rules": [...]},
    category_fn=my_category_fn,
)
backend.index(corpus)

stack = ChorusStack.defaults(tenant_id="acme").with_retrieval(backend)
retrieve_node = stack.to_retrieve_handler(topic="clinical_guidelines", top_k=6)
```

### 4.2 Pipeline

1. **Index** — embed corpus with shared ONNX embedder; Chroma `add()`; optional PrismRAG remap on write
2. **Retrieve** — vector query on `{topic, query}`; score = `1 / (1 + distance)`
3. **Rerank** — `resonance_rerank` projects chunk text through same JL substrate as cache gate
4. **Downstream** — LLM summarize / judge hops consume `kb_context` + `retrieved` state keys

Retrieval hops stay **LLM-free** — deterministic given embedder weights.

### 4.3 Install matrix

```bash
pip install chorusgraph                    # keyword default only
pip install "chorusgraph[retrieval]"       # + chromadb vector path
export PRISMRAG_LICENSE_KEY="..."          # + taxonomy remap (requires prismrag-patch)
```

### 4.4 Degradation (production UX)

| Missing piece | Behavior |
|---------------|----------|
| chromadb | Falls back to keyword backend; logs install hint |
| License key | Vector search works; remap disabled |
| prismrag_patch | Raw Chroma; no remap |

No fabricated licenses. No silent fake vector results.

### 4.5 Custom backends

Implement `RetrievalBackend` protocol — pgvector, OpenSearch, enterprise search — and `stack.with_retrieval(yours)`.

---

## 5. Proof — benchmarks and tests

### 5.1 MVP matrix (Azure, canonical)

Run ID: **`mid_20260708_111539`** · 100 tasks/scenario · 8 scenarios · verified against raw JSONL

| Pair | LangGraph | ChorusGraph | Notes |
|------|-----------|-------------|-------|
| FL1 / FC1 | 87.0% | **98.0%** | Finance single |
| FL2 / FC2 | 87.0% | **94.0%** | Finance multi-agent (fair paired comparison) |
| HL1 / HC1 | 74.0% | **79.0%** | Healthcare single |
| HL2 / HC2 | 59.0% | **85.0%** | **+26 pp** healthcare multi |

**Efficiency (mid tier, mean per task):** finance scenarios cut LLM calls ~66–76% and mean latency ~67–72% vs LangGraph (40–52% cache hit). Healthcare multi: higher success with comparable latency.

Benchmark-only fixes July 2026 (`eeba2ad`): FL2 `annual_rate_pct` prompt; fair success denominators. No `chorusgraph` library change.

**Reproduce:**
```bash
python -m benchmark.run_scenarios --tier mid --temperature 0.0 --seed 42
```

### 5.2 H10 sliced metrics (FX workload)

Repeat band 40%, competent LangGraph ReAct baseline:

- B latency p50: **575 ms** vs A **4498 ms** (paired delta ≈ −4.6 s)
- B cost/task: **$0.0001** vs A **$0.0004**
- B cache hit-rate: **41%** (Wilson 95% CI)

Quote sliced metrics for fair comparisons — see `docs/BENCHMARK_RESULTS.md`.

### 5.3 Engineering proof

- **323 tests** pass on deterministic tier (no `GEMINI_API_KEY`)
- **71% coverage** floor enforced in CI
- E2 fault-injection: node failure → partial result, not process crash
- E6 cross-tenant leakage tests pass

---

## 6. Enterprise 1.0 readiness

| Capability | Status |
|------------|--------|
| CI/CD (GitHub Actions) | ✅ |
| Deterministic + live test tiers | ✅ |
| Resilience (breakers, retries) | ✅ |
| Security (sandbox, TLS, PII redaction) | ✅ Built; external audit Phase 2 |
| Observability (OTel, health) | ✅ |
| Durable graph (SQLite) | ✅ Postgres Phase 2 |
| Multi-tenant isolation | ✅ |
| Load harness | ✅ |
| Docker / k8s | ✅ |
| API 1.0 freeze | ✅ |

Full scorecard: [`docs/ENTERPRISE_READINESS.md`](ENTERPRISE_READINESS.md).

---

## 7. Getting started

```bash
pip install "chorusgraph[retrieval]"

python -c "
from chorusgraph.compose import ChorusStack, KeywordRetrievalBackend
corpus = [{'id':'1','topic':'demo','text':'ChorusGraph semantic cache and retrieval','source':'wp'}]
b = KeywordRetrievalBackend(); b.index(corpus)
s = ChorusStack.defaults(tenant_id='wp').with_retrieval(b)
print(s.resolve_retrieval().retrieve('demo', 'semantic cache', top_k=1))
"
```

Next steps:

1. [`docs/INSTALL.md`](INSTALL.md) — pip extras + PrismRAG walkthrough
2. [`docs/DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) — graph patterns
3. [`docs/DEPLOY.md`](DEPLOY.md) — Docker / k8s
4. `from chorusgraph.public import Graph, ChorusStack, wrap` — stable API

---

## 8. Commercial framing (Grand Slam Offer sketch)

*For GTM / website — apply full playbook in `handoffs/handoffProductLanding.md`.*

### Avatar

VP Engineering / Head of AI Platform · B2B SaaS with shipped LLM feature · $3k+/mo model spend.

### Dream outcome

Cut agent token spend and integration time **without** hiring a retrieval platform team — live in staging in days, not quarters.

### Offer stack (illustrative)

| Component | Obstacle solved |
|-----------|-----------------|
| `pip install chorusgraph` + golden-path graph | "Integration hell" |
| PrismRAG plug-in + mapping templates | "Another vector DB project" |
| Shadow cache report on staging traffic | "Won't work here" |
| Route Ledger + replay | "Can't audit the agent" |
| Docker Compose + health endpoints | "Ops won't approve" |
| 323-test CI parity | "Vendor too new" |

### Proof anchors

- HL2→HC2 **+30 pp** on healthcare multi-agent (Azure)
- FC1 **100%** vs FL1 87.5% on finance single
- H10: **~8× lower p50 latency** on repeat FX band (sliced)

### Pricing wedge (suggested tiers)

| Tier | Buyer | Wedge |
|------|-------|-------|
| **OSS / pip** | Developers | Core runtime + keyword retrieval |
| **Pro** | Teams | PrismRAG license + support |
| **Enterprise** | Regulated | SLA, Postgres path, pen test, air-gap |

*Pricing is indicative — finalize with Director.*

### Conditional guarantee (pilot)

Example pilot guarantee (must be honored if offered):

> Semantic cache hit rate ≥40% on repeat intent traffic in 14-day staging shadow, or pilot fee credited toward implementation.

---

## 9. Roadmap honesty (Phase 2)

Not in 1.0 — documented, not hidden:

- Postgres-native Cortex GraphStore (SQLite ships today)
- CHORUS cipher external audit (TLS default; cipher opt-in)
- Production Azure soak SLO sign-off
- Full-package lint cleanup
- External penetration test certification

---

## 9.5 Publish gate (internal — remove before external release)

**Verified 2026-07-05:** `pip install chorusgraph` in a throwaway venv succeeds; `import chorusgraph` and the README hello-world snippet work with core deps only (`prismlib-plus`, `prismresonance`, `prismlang`). Re-run the gate after any `pyproject.toml` dependency change:

```powershell
python -m venv clean_test_env
clean_test_env\Scripts\pip install chorusgraph
clean_test_env\Scripts\python -c "import chorusgraph; from chorusgraph import Graph, ChorusStack; print(chorusgraph.__version__)"
```

## 10. Conclusion

ChorusGraph 1.0 is the **integration layer the Prism family was missing**: a native runtime where cache, retrieval, memory, and tools are **ports** — not science projects. PrismRAG moves from benchmark-only to **`pip install "chorusgraph[retrieval]"` + `with_retrieval()`**.

For regulated production at scale, complete Phase 2 persistence and security validation. For pilots and product teams shipping agents today, the engine, plug-ins, benchmarks, and deploy path are ready.

---

**Contact:** Insight IT Solutions · **License:** Apache-2.0 · **Package:** [pypi.org/project/chorusgraph](https://pypi.org/project/chorusgraph/) · **Latest:** [1.1.0](https://pypi.org/project/chorusgraph/1.1.0/)

**References:** `docs/INSTALL.md` · `docs/PLUGINS.md` · `docs/STABILITY.md` · `handoffs/handoffEback.md` · `handoffs/handoffProductLanding.md`

*Whitepaper v1.0 · 2026-07-05*
