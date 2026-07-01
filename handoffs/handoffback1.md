# Handoff 1 — Return · Senior Engineer (Cursor) → Architect

## 1. Summary

Built the **ChorusGraph runnable spine**: a standalone `chorusgraph` Python package that wraps any compiled LangGraph `StateGraph` **without modifying it**, observes execution via LangGraph's `stream_mode="debug"` API, and persists a **Route Ledger** (per-node steps, conditional branches, `rule_chain`, timing, and nullable cache/grounding slots) to SQLite (default) or Postgres.

Shipped: package skeleton, `RouteLedger` model, `SqliteLedgerSink` + `PostgresLedgerSink`, `wrap()` adapter, an LLM-free demo graph with real `prismlang` `@prism_node`, pytest suite (real components, no mocks), and a successful stretch run against the real `website_hub` greeting path.

Skipped OpenTelemetry spans (not trivial without adding a hard dependency and span lifecycle wiring — candidate for Handoff 2).

## 2. File tree

```
C:\code\ChorusGraph\
├── pyproject.toml
├── chorusgraph/
│   ├── __init__.py
│   ├── adapter/
│   │   ├── __init__.py
│   │   └── wrap.py              # wrap(), RunnableWithLedger
│   ├── examples/
│   │   ├── __init__.py
│   │   └── demo_graph.py        # primary demo (LLM-free, real PrismLang)
│   └── ledger/
│       ├── __init__.py
│       ├── models.py            # RouteLedger, LedgerStep
│       ├── query.py             # get_run(), list_runs()
│       └── sink.py              # SqliteLedgerSink, PostgresLedgerSink
├── tests/
│   ├── __init__.py
│   ├── test_adapter.py
│   └── test_ledger.py
└── handoffs/
    └── handoffback1.md          # this file
```

## 3. How to run

```powershell
cd C:\code\ChorusGraph
pip install -e ".[dev]"

# Primary demo (short + long conditional branches)
python -m chorusgraph.examples.demo_graph

# Full test suite
pytest -v

# Postgres smoke test (optional — requires running Postgres)
$env:CHORUSGRAPH_TEST_POSTGRES_DSN = "postgresql://user:pass@localhost:5432/chorusgraph_test"
pip install -e ".[postgres]"
pytest -v tests/test_ledger.py::test_postgres_smoke
```

Stretch demo is exercised automatically when `C:\code\InsightitsAIAgent\meeting-scheduler\website_hub\graph.py` exists (test `test_website_hub_greeting_stretch_demo`).

## 4. Test results

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\code\ChorusGraph
configfile: pyproject.toml
testpaths: tests
collected 6 items

tests/test_adapter.py::test_demo_graph_short_path_records_nodes_and_branch PASSED
tests/test_adapter.py::test_demo_graph_long_path_branch PASSED
tests/test_adapter.py::test_list_runs_by_graph_and_tenant PASSED
tests/test_adapter.py::test_website_hub_greeting_stretch_demo PASSED
tests/test_ledger.py::test_sqlite_write_and_query_roundtrip PASSED
tests/test_ledger.py::test_postgres_smoke SKIPPED (Set CHORUSGRAPH_TEST_POSTGRES_DSN)

======================== 5 passed, 1 skipped in ~1s =========================
```

Demo output (short path, abbreviated):

```json
{
  "result": { "response": "short:hi", "route": "short_path" },
  "ledger": {
    "steps": [
      { "node": "analyze", "edge_taken": "route_decision", "rule_chain": ["text -> encoder(all-MiniLM-L6-v2, d=384)", "..."] },
      { "node": "route_decision", "edge_taken": "short_path", "rule_chain": ["score_lte_5", "route=short_path"] },
      { "node": "short_path" }
    ]
  },
  "persisted_match": true
}
```

Website hub stretch (greeting turn): nodes `resolve_session → classify_intent → respond_quick`, branch `respond_quick`, ~4 ms, no LLM.

## 5. Key decisions & deviations

| Decision | Rationale |
|----------|-----------|
| **`stream_mode="debug"` as primary observation API** | Reliably emits `task` / `task_result` events with node names. Conditional edge destination is encoded in the *next* task's `triggers` as `branch:to:<node>`. |
| **Edge attribution via next-task trigger** | `astream_events` exposes router chains (`on_chain_start name=route`) but not a clean edge label; `updates` gives node outputs but not edge names. Debug triggers are the only source that names the destination node. |
| **Linear edges also get `edge_taken`** | Linear and conditional edges use the same `branch:to:` trigger format — indistinguishable in the API. We record the destination node on the prior step for both. Acceptable for observability; flag if ADR-003 wants `edge_taken=null` on non-conditional hops. |
| **`rule_chain` from step result, not cumulative state** | Prism `@prism_node` puts `rule_chain` inside `prism_sequence` envelopes; router nodes can set top-level `rule_chain`. Terminal nodes no longer inherit the router's chain. |
| **SQLite single persistent connection** | `:memory:` SQLite otherwise creates a fresh DB per connection; one connection per sink fixes re-query after write. |
| **Postgres sink ships; smoke test gated on env DSN** | Interface parity with SQLite; no local Postgres in CI — skipped unless `CHORUSGRAPH_TEST_POSTGRES_DSN` is set. |
| **Standalone `chorusgraph` package name** | Per brief: namespace vs `prismlib-plus[orchestrator]` is an open director decision — did not block. |
| **No OTel** | Would need optional `opentelemetry-api` + span parent linking per step; deferred. |

## 6. Blockers / issues hit

**Stretch demo (`website_hub`): succeeded.** No blocker.

- Greeting path (`message="hello"`) runs deterministically: `resolve_session → classify_intent → respond_quick`.
- Heavy paths (RAG + Gemini + pgvector) were not exercised in this handoff — by design (LLM-free acceptance criteria).
- `website_hub` is outside this repo; stretch test adds `meeting-scheduler` to `sys.path` when present locally.

**LangGraph rough edge:** `branch:to:<node>` triggers do not distinguish conditional vs unconditional edges, and do not include the router function name or branch key (e.g. `greeting` vs `respond_quick`). We record the resolved destination node, which matches graph semantics.

## 7. Answers to §6 open questions

### Q1 — Which LangGraph event API reliably exposed node **and** edge transitions?

| API | Nodes | Edges | Verdict |
|-----|-------|-------|---------|
| **`stream_mode="debug"`** | Yes — `task` / `task_result` with `payload.name` | Partial — next task's `payload.triggers` contains `branch:to:<dest>` | **Primary choice** |
| `stream_mode="updates"` | Yes — dict keys are node names | No — no edge metadata | Supplement only |
| `stream_mode="values"` | No — full state snapshots only | No | Not useful for ledger |
| `astream_events(v2)` | Yes — `metadata.langgraph_node` | Router runs as `on_chain_start name=route` but **no branch label** | Useful for timing/debug, not edge ledger |

### Q2 — Did the stretch demo run?

**Yes.** Real `website_hub.get_graph()`, greeting turn, ledger persisted and queryable. See test `test_website_hub_greeting_stretch_demo`.

### Q3 — Anything in DESIGN §5/§7/§11 wrong or awkward against real LangGraph?

1. **§11 adapter assumption:** Design implies rich edge/router observability. In practice, edge decisions are inferred from debug triggers, not first-class events. Router functions are invisible except as brief `on_chain_*` spans.
2. **§7 Route Ledger + `rule_chain`:** Hubs do not put `rule_chain` at state top-level today — it lives in `prism_sequence` envelopes (PrismLang) and `meta.orchestrator.reason` (routing). Adapter handles both; design should document these as the real sources.
3. **§5.3 Postgres for ledger:** Reasonable. Checkpoint coordinator is separate from Route Ledger — don't conflate schemas.

### Q4 — Postgres ledger schema recommendation (ADR-003)

**MVP (shipped):** single table, JSON steps blob — fast to ship, matches SQLite.

**Production recommendation:**

```sql
-- Run header
CREATE TABLE route_ledgers (
    run_id       UUID PRIMARY KEY,
    turn_id      TEXT,
    tenant_id    TEXT NOT NULL,
    graph_id     TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ledgers_tenant_graph ON route_ledgers (tenant_id, graph_id, created_at DESC);

-- Normalized steps (queryable per node / cache hit)
CREATE TABLE route_ledger_steps (
    run_id           UUID NOT NULL REFERENCES route_ledgers(run_id) ON DELETE CASCADE,
    step_index       INT  NOT NULL,
    node             TEXT NOT NULL,
    edge_taken       TEXT,
    rule_chain       JSONB,
    duration_ms      INT  NOT NULL DEFAULT 0,
    timestamp        TIMESTAMPTZ NOT NULL,
    cache_hit        BOOLEAN,
    cache_score      DOUBLE PRECISION,
    grounding_score  DOUBLE PRECISION,
    PRIMARY KEY (run_id, step_index)
);
CREATE INDEX idx_steps_node ON route_ledger_steps (node);
CREATE INDEX idx_steps_cache ON route_ledger_steps (cache_hit) WHERE cache_hit IS NOT NULL;
```

Add retention/partitioning by `created_at` and PII redaction policy (DESIGN §21 #7) before production.

### Q5 — PrismCache embedder / HashEmbedder fallback

**Yes, real embedder by default:** `PrismCache.build()` tries `SentenceTransformerEmbedder()` (all-MiniLM-L6-v2, 384-d) first (`prism/cache/cache.py:249-251`).

**HashEmbedder fallback:** triggers on *any* exception from SentenceTransformer construction (broad `except Exception`), logs a warning, silently continues (`cache.py:252-258`). It is **not semantically meaningful** (`embedder.py:401-418`).

**Make it fail loudly:**

```python
# In PrismCache.build() — replace broad except with:
from prism.cache.embedder import EmbedderNotInstalledError, SentenceTransformerEmbedder

embedder = SentenceTransformerEmbedder()  # let EmbedderNotInstalledError propagate

# Or explicit policy flag:
if os.environ.get("PRISM_CACHE_ALLOW_HASH_EMBEDDER") != "1":
    raise RuntimeError("Refusing HashEmbedder in production; install sentence-transformers")
```

Also add a startup health check that embeds a canary pair and asserts cosine similarity > 0.5.

### Q6 — ClusterCache backing / sync store

`ClusterCache` (`prism/cluster/cache.py`) layers on top of:

1. **Local `PrismCache`** — per-node RAM or SQLite (`InMemoryStore` / `SQLiteStore`).
2. **In-process cluster dict** — `self._cluster_entries: dict[str, ClusterCacheEntry]` (RAM, per node).
3. **CHORUS Fabric** — `emit_event` / `ingest_cluster_frame` for `TOKEN_SYNC` frames to share entries across nodes.

Cluster cache is **ephemeral RAM + CHORUS gossip**, not Postgres/Redis. Document: *"L1 response cache is per-node RAM/SQLite; cross-node sharing is via ClusterCache in-memory + CHORUS TOKEN_SYNC, not a shared database."*

## 8. Design contradicted by reality

1. LangGraph does not emit explicit "conditional edge X taken" events — only implicit `branch:to:` on the downstream task.
2. `rule_chain` in design reads like a universal state field; in hubs it's primarily inside `PrismEnvelope` in `prism_sequence`.
3. DESIGN §22 OTel — trivial in principle, but wiring parent spans to debug-task boundaries needs deliberate SDK integration (skipped this slice).

## 9. Proposed scope for Handoff 2

1. **Instrument `cache_hit`, `cache_score`, `grounding_score`** on ledger steps by hooking PrismCache `get_or_call` and grounding guard (fields exist, always null today).
2. **Two-stage `cache_gate`** (§8.1) on a reference graph + shadow FP measurement.
3. **Normalize Postgres steps table** (ADR-003) + migration from JSON blob.
4. **OpenTelemetry exporter** for ledger steps (optional span per node).
5. **Adapter edge semantics** — graph introspection to mark conditional vs linear edges so `edge_taken` is null on linear hops.
6. **PrismCache embedder fail-loud** patch upstream (or wrapper in ChorusGraph policy engine).

---

*Handoff 1 complete · 5 pytest passed · stretch demo passed · no mocks · hub code untouched.*
