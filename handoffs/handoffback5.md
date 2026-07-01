# Handoff 5 — Return · Senior Engineer (Cursor) → Architect

## 1. Summary

Shipped **dual memory** for the finance agent (v0.5.0):

1. **PrismCheckpointer** (`chorusgraph/checkpoint/`) — LangGraph checkpointer via `SqliteSaver` (local) with optional Postgres factory. Thread state (`conversation_history`, graph position) survives a simulated process restart.
2. **Cortex L3 memory** (`chorusgraph/memory/`) — real `prism_memory()` stack with async salience-gated digest, profile-aware `recall_for_turn()`, and `explain()` provenance.
3. **Ledger grounding** — `writer` step `grounding_score` populated from `recall().confidence` when memory is used.

Function-first: the agent **remembers correctly** across thread resume and cross-session recall. No performance/cost measurement.

**40 passed, 1 skipped** (`pytest -v`).

## 2. File tree

```
C:\code\ChorusGraph\
├── pyproject.toml                              # v0.5.0, langgraph-checkpoint-sqlite, cortex optional
├── chorusgraph/
│   ├── checkpoint/
│   │   ├── __init__.py
│   │   └── prism.py                            # PrismCheckpointer, create_checkpointer()
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── cortex_service.py                   # get_cortex_service(), recall_for_turn()
│   │   ├── async_digest.py                     # background digest + sleep
│   │   └── recall.py                           # prompt formatting
│   ├── adapter/wrap.py                         # grounding_score on writer ledger steps
│   ├── ledger/instrument.py                    # make_memory_step()
│   └── examples/finance_agent/
│       ├── graph.py                            # compile(checkpointer=...)
│       ├── nodes.py                            # recall injection, history append
│       ├── runtime.py                          # Cortex + schedule_turn_digest()
│       └── run_memory_demo.py                  # thread resume + cross-session demo
├── tests/
│   ├── test_checkpoint.py
│   └── test_memory.py
└── handoffs/
    └── handoffback5.md
```

## 3. How to run

```powershell
cd C:\code\ChorusGraph
pip install -e ".[dev,gemini,cortex]"

$env:GEMINI_API_KEY = "<your-key>"

pytest -v

# Memory demos (thread resume + cross-session recall)
python -m chorusgraph.examples.finance_agent.run_memory_demo
# or: chorusgraph-finance-memory
```

## 4. Test results

```
============= 40 passed, 1 skipped, 1 warning in ~70s =============
```

## 5. Real run output

### Demo A — Thread resume after restart (PrismCheckpointer / SQLite)

```
Turn 1: USD→EUR rate (checkpoint saved)
Turn 2: USD→GBP follow-up (conversation_history = 4 entries)

>>> Simulating process restart (new SQLite connection, same file) <<<
Restored conversation_history entries: 4

Turn 3: "Given our earlier rates, which is stronger against USD — EUR or GBP?"
Answer: ... 1 USD = 0.8785 EUR ... EUR is stronger against USD than GBP ...
conversation_history after turn 3: 6 entries
```

### Demo B — Cross-session Cortex recall (new thread, same memory service)

```
Session 1 (thread session-1-*):
  User: "My risk tolerance is conservative. I prefer low-volatility investments..."
  [async digest scheduled — off response path]

Session 2 (thread session-2-*, new thread):
  User: "What kind of bond allocation would you recommend for me?"
  memory_recall: "The user's stated preferences are low-volatility investments and
                  capital preservation. The user's risk tolerance is conservative..."
  memory_confidence: 0.5
  Ledger writer grounding_score: 0.5
  Answer: "...Given your conservative investment profile... bond allocation should
           prioritize low-volatility and capital preservation..."

explain("What is my risk tolerance?"):
  confidence: 0.5
  evidence:
    - risk tolerance is conservative (source_id=session1-turn1)
    - user prefers low-volatility investments (source_id=session1-turn1)
    - user prefers capital preservation (source_id=session1-turn1)
```

## 6. Decisions / deviations

| Decision | Rationale |
|----------|-----------|
| **SqliteSaver as PrismCheckpointer backend** | Implements LangGraph `BaseCheckpointSaver` correctly; Postgres via optional `langgraph-checkpoint-postgres`. |
| **`recall_for_turn()` profile fallback** | Direct `recall(bond_question)` often returns "I do not have that information yet."; fallback queries for user preferences retrieve stored facts. |
| **Process-wide `get_cortex_service()` singleton** | Shares `InMemoryGraphStore` across threads/sessions within one process — required for cross-session recall per §3 KNOWN CONSTRAINT. |
| **ThreadPoolExecutor for digest** | Returns immediately from `schedule_digest()`; `wait_for_digest()` for demo/test synchronization. |
| **Validator appends `conversation_history`** | Enables checkpointer to persist multi-turn state without manual history passing. |
| **Empty recall answers filtered** | Prevents injecting "I do not have that information yet." as memory context. |

## 7. Blockers / open items

- **InMemoryGraphStore not durable across Cortex process restart** — documented per handoff §3; durable GraphStore is a future item. Checkpointer covers *conversation* durability; Cortex graph durability does not.
- **`google.generativeai` deprecated** — finance agent still uses it; Cortex uses `google-genai`. Unify in H6.
- **Floating Gemini model aliases** — PrismCortex warns about unpinned `gemini-2.5-flash`.

## 8. Answers to Handoff 5 §7

### 1. Checkpointer backend and LangGraph hook?

**SQLite** via `langgraph.checkpoint.sqlite.SqliteSaver`, wrapped by `create_checkpointer("sqlite", path=...)` / `PrismCheckpointer()`. Graph compiled with `graph.compile(checkpointer=cp)`. Each invoke passes `config={"configurable": {"thread_id": "..."}}`. Postgres available via `create_checkpointer("postgres", conn_string=...)` + `[postgres-checkpoint]` extra.

### 2. How async digest is scheduled?

`AsyncDigester` uses a **ThreadPoolExecutor** (2 workers). `schedule_turn_digest()` submits after the response returns — digest never blocks the graph invoke. Cortex `digest()` handles salience gating internally (`SKIP_BANDS` skip trivial turns without LLM). Staged facts trigger background `sleep()`.

### 3. Cross-session recall with in-memory GraphStore?

**Yes**, while the process/service stays up. Session 2 (new `thread_id`) recalled conservative preference with provenance via `explain()`. Surprise: direct question-level `recall()` misses unless profile fallback query is used — fixed with `recall_for_turn()`.

### 4. Durable-across-restart Cortex needed for first release?

**Can wait.** Checkpointer covers thread/conversation resume for production workflows. Cortex graph persistence matters for long-lived agent services that restart frequently — flag as Phase 2 alongside multi-DB GraphStore connectors (DESIGN §13.4). Answer cache (PrismLib SQLite) already survives restart but graph facts do not.

### 5. Proposed H6 scope (execution patterns)

1. **ReAct / Reflection / Plan-Solve** on role scaffold (DESIGN §7.6).
2. **HITL interrupts** on `ValidatorNode` rejection — enabled by checkpointer.
3. **Durable Cortex GraphStore** — Postgres or customer datastore.
4. **A/B benchmark (Container B)** — latency, cost, FP measurement (deferred since H4).
5. **Migrate finance Gemini client** to `google.genai`.

## 9. Design contradictions

- DESIGN §5.3 names "PrismCheckpointer on Postgres" as primary; H5 ships SQLite-first (Postgres factory ready) — pragmatic for local dev and demos.
- Cortex auto-digest is async per §13.3, but cross-session demo requires `wait_for_digest()` in tests — production would rely on eventual consistency without blocking.
- `recall_for_turn()` profile fallback is orchestrator logic not in raw Cortex — necessary because renderer returns "no information" for questions outside stored fact vocabulary.

## 10. Acceptance criteria checklist

- [x] Thread resumes from checkpoint after process restart
- [x] Fact from session 1 recalled in session 2 with `explain()` provenance
- [x] Auto-digest async and salience-gated (trivial turns skipped)
- [x] Ledger `grounding_score` from Cortex confidence when memory used
- [x] Real prismcortex/Gemini — no mocks; pytest green
- [x] No performance numbers reported

---
*Handoff 5 · architect: Claude · the agent remembers · v0.5.0*
