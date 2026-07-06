# Install ChorusGraph (pip)

**Package:** `chorusgraph` · **Version:** 1.0.1 · **Python:** ≥3.11 · **License:** Apache-2.0

---

## Quick install

```bash
# Core runtime (native engine + PrismLang + semantic cache defaults)
pip install chorusgraph

# With vector retrieval (Chroma + PrismRAG plugin)
pip install "chorusgraph[retrieval]"

# Full developer / CI tier
pip install "chorusgraph[dev,gemini,retrieval]"

# Enterprise deploy extras
pip install "chorusgraph[postgres,cortex,gemini,retrieval]"
```

Verify:

```bash
python -c "import chorusgraph; print(chorusgraph.__version__)"
python -m pytest --version   # if dev extra installed
```

---

## Optional dependency groups

| Extra | Installs | When you need it |
|-------|----------|------------------|
| *(none)* | Core runtime (`prismlang`, `prismlib-plus`, `prismresonance`) | Default stack — semantic cache + resonance bus ship with `pip install chorusgraph` |
| `retrieval` | `chromadb>=0.4` | `PrismRAGRetrievalBackend` vector search |
| `gemini` | `google-genai` | Live Gemini examples and `-m live` tests |
| `cortex` | `prismcortex[prism,gemini]` | L3 structured memory (PrismCortex) |
| `postgres` | `psycopg[binary]` | Postgres DSN paths in deploy docs |
| `benchmark` | chromadb + langgraph | FL*/HL* LangGraph baseline scenarios only |
| `langgraph` | langgraph + checkpoint-sqlite | Baselines / compat tests — **not** required for core product |
| `postgres-checkpoint` | LangGraph Postgres checkpointer | Durable checkpoints on Postgres (optional) |
| `benchmark-healthcare` | `chromadb` | Healthcare benchmark scenarios (HC1/HC2) |
| `dev` | pytest, ruff, mypy, coverage, SBOM tools | Contributing / CI parity |
| `enterprise-ci` | dev + gemini + benchmark-healthcare | Full CI matrix locally |

Lockfile for reproducible installs: `requirements-lock.txt` (see [`RELEASE.md`](RELEASE.md)).

**LangGraph is not a dependency of ChorusGraph's own code.** `pip install chorusgraph` gives you the native engine only — the scheduler and all four ports never import LangGraph. (`prismlang`, a core dependency, uses LangGraph internally for its own checkpointing utilities, so it will still show up in a dependency-tree scan — that's `prismlang`'s implementation detail, not something ChorusGraph's engine calls.) Install `chorusgraph[benchmark]` when running FL*/HL* comparison scenarios or compat conformance tests.

---

## 60-second hello world

```python
from chorusgraph import Graph, START, END, ChorusStack
from chorusgraph.core.node import dict_node_adapter

stack = ChorusStack.defaults(tenant_id="demo")

g = Graph(tenant_id="demo", graph_id="hello")
g.add_node("echo", dict_node_adapter(lambda s: {"reply": f"Hello, {s.get('name', 'world')}"}, hop="echo"))
g.add_edge(START, "echo")
g.add_edge("echo", END)

out = g.compile(stack=stack).invoke({"name": "ChorusGraph"})
print(out)  # {'reply': 'Hello, ChorusGraph'}
```

Run the bundled demo:

```bash
chorusgraph-demo
```

### Pre-install audit (no API key)

Estimate cache hit rate from your own query logs (CSV/JSONL) using the real semantic gate:

```bash
chorusgraph-audit --log your_queries.jsonl
chorusgraph-audit --log your_queries.csv --json -o audit_report.json
```

After a Production Agent Pilot, report **measured** cache hits from the Route Ledger:

```bash
chorusgraph-audit --list-runs --ledger-db .chorusgraph/ledger.db
chorusgraph-audit --ledger <run_id> --ledger-db .chorusgraph/ledger.db
```

Live ledger reports include hit rate and latency; dollar estimates require a future `LedgerStep` token-field addition.

---

## Plug-in architecture (four swappable ports)

Install once; swap backends without changing graph code. Full reference: [`PLUGINS.md`](PLUGINS.md).

| Port | Default (zero extra deps) | Common swap |
|------|---------------------------|-------------|
| Cache | `PrismCacheBackend` | `RedisCacheBackend` |
| Memory | `CortexMemoryBackend` | `enable_memory=False` |
| Tools | Finance registry | Custom `ToolRegistry` |
| **Retrieval** | `KeywordRetrievalBackend` | **`PrismRAGRetrievalBackend`** |

```python
from chorusgraph.compose import ChorusStack, RedisCacheBackend

stack = (
    ChorusStack.defaults(tenant_id="acme")
    .with_cache(RedisCacheBackend(tenant_id="acme"))
)
```

---

## PrismRAG retrieval plugin — implementation guide

PrismRAG is an **opt-in L2 retrieval backend** on `ChorusStack`. It follows the same pattern as the Redis cache swap: implement or configure a backend, call `with_retrieval()`, wire a retrieve node.

### What you get

| Mode | Dependencies | Behavior |
|------|--------------|----------|
| **Keyword (default)** | None | Token overlap on your indexed corpus |
| **Vector** | `pip install "chorusgraph[retrieval]"` | Chroma in-process nearest-neighbor |
| **Vector + taxonomy remap** | Above + `prismrag-patch` + `PRISMRAG_LICENSE_KEY` | Category-aware re-embedding via PrismRAG |

Retrieval is **deterministic** (no LLM in the retrieve hop). Results feed `make_retrieve_handler` → PrismResonance rerank on the shared 64-d PrismLang substrate.

### Step 1 — Install extras

```bash
pip install "chorusgraph[retrieval]"
# Optional licensed remap (separate package — contact Insight IT / PrismLab):
# pip install prismrag-patch
export PRISMRAG_LICENSE_KEY="your-license-key"   # Linux/macOS
# $env:PRISMRAG_LICENSE_KEY = "your-key"        # PowerShell
```

### Step 2 — Prepare your corpus

Each document needs at minimum:

```python
corpus = [
    {
        "id": "doc-001",
        "topic": "billing",           # domain slug / category hint
        "text": "Full chunk text…",
        "source": "kb/internal/v2",   # provenance
    },
    # ...
]
```

### Step 3 — Define taxonomy mapping (for PrismRAG remap)

Mapping matches `prismrag_patch` contract: `categories` + keyword `rules`.

```python
mapping = {
    "categories": [
        {"slug": "billing", "label": "Billing"},
        {"slug": "security", "label": "Security"},
    ],
    "rules": [
        {"word": "invoice", "category_slug": "billing"},
        {"word": "pci", "category_slug": "security"},
    ],
}

def assign_category(text: str) -> str | None:
    lower = (text or "").lower()
    scores: dict[str, int] = {}
    for rule in mapping["rules"]:
        if rule["word"] in lower:
            scores[rule["category_slug"]] = scores.get(rule["category_slug"], 0) + 1
    return max(scores, key=scores.get) if scores else None
```

### Step 4 — Build backend and stack

```python
from chorusgraph.compose import ChorusStack, PrismRAGRetrievalBackend, KeywordRetrievalBackend
from chorusgraph.embedders import PrismlangOnnxEmbedder

# Option A — zero-deps keyword (good for tests / small corpora)
kw = KeywordRetrievalBackend()
kw.index(corpus)
stack = ChorusStack.defaults(tenant_id="acme").with_retrieval(kw)

# Option B — vector + optional PrismRAG remap
prism = PrismRAGRetrievalBackend(
    embedder=PrismlangOnnxEmbedder(),
    mapping=mapping,
    category_fn=assign_category,
    collection_name="acme_knowledge_base",  # isolate collections per tenant/product
    # license_key="..."  # or PRISMRAG_LICENSE_KEY env
)
prism.index(corpus)
stack = ChorusStack.defaults(tenant_id="acme").with_retrieval(prism)
```

**Graceful degradation:**

- No `chromadb` → logs warning, uses internal keyword backend
- No license key → vector search runs; taxonomy remap disabled (logged)
- Invalid / missing `prismrag_patch` → raw Chroma query without remap

### Step 5 — Wire retrieve node into your graph

```python
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

runtime = FinanceRuntime(tenant_id="acme", stack=stack, enable_cortex=False)

# Ready-made handler (PrismResonance rerank + cache projection)
retrieve_node = stack.to_retrieve_handler(topic="billing", top_k=6, runtime=runtime)

# Use in graph — dict adapter example:
from chorusgraph.core.node import dict_node_adapter

def retrieve(state):
    update = retrieve_node(state)
    return update

g.add_node("retrieve", dict_node_adapter(retrieve, hop="retrieve"))
```

Or call retrieval directly (no graph):

```python
chunks = stack.resolve_retrieval().retrieve("billing", "invoice due date", top_k=6)
for c in chunks:
    print(c["id"], c["category_slug"], c["score"], c["text"][:80])
```

### Step 6 — Chunk shape (contract)

Every backend returns:

```python
{
    "id": str,
    "topic": str,
    "text": str,
    "source": str,
    "category_slug": str,
    "score": float,          # relevance
    # Optional after rerank:
    "resonance_score": float,
    "prismrag_category": str,
}
```

### Step 7 — Custom `RetrievalBackend`

Implement the protocol in `chorusgraph.compose.ports`:

```python
class MyPgVectorBackend:
    name = "pgvector"
    _chorusgraph_retrieval_backend = True

    def index(self, corpus): ...
    def retrieve(self, topic: str, query: str, *, top_k: int = 6) -> list[dict]: ...

stack = ChorusStack.defaults(tenant_id="acme").with_retrieval(MyPgVectorBackend())
```

Set `_chorusgraph_retrieval_backend = True` or use `is_retrieval_backend(obj)`.

### Healthcare reference implementation

Production-shaped example (domain data stays in benchmark; machinery is library):

```python
from benchmark.healthcare.retrieval import build_clinical_retrieval_backend

stack = ChorusStack.defaults(tenant_id="healthcare").with_retrieval(
    build_clinical_retrieval_backend()
)
```

See `benchmark/healthcare/retrieval.py` for mapping + corpus wiring.

---

## Deploy after install

| Path | Doc |
|------|-----|
| Docker Compose / k8s | [`DEPLOY.md`](DEPLOY.md) |
| Health checks | `curl http://localhost:8080/health` |
| Observability | [`docs/runbooks/COMMON_FAILURES.md`](runbooks/COMMON_FAILURES.md) |

---

## Public API & stability

- Frozen 1.0 surface: [`API_1_0.md`](API_1_0.md) · `from chorusgraph.public import …`
- Plug-in adapters (including retrieval): `from chorusgraph.compose import …`
- Stability policy: [`STABILITY.md`](STABILITY.md)

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `chromadb not installed` warning | `pip install "chorusgraph[retrieval]"` |
| Empty retrieve results | Call `.index(corpus)` before `.retrieve()` |
| Resonance rerank returns 0 chunks | Omit `query_vector_64` from state for keyword-only path, or lower `min_constructive_score` in `RetrieveConfig` |
| PrismRAG remap not active | Set `PRISMRAG_LICENSE_KEY`; install `prismrag-patch` |
| Live Gemini tests skipped | `pip install "chorusgraph[gemini]"` + `GEMINI_API_KEY` + `pytest -m live` |

---

## Next reads

- [`PLUGINS.md`](PLUGINS.md) — all four ports
- [`COMPOSE.md`](COMPOSE.md) — `ChorusStack` architecture
- [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) — graph patterns
- [`WHITEPAPER.md`](WHITEPAPER.md) — product thesis + benchmark proof
- [`RELEASE.md`](RELEASE.md) — semver, tags, SBOM
