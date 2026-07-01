# Handoff 4 — Return · Senior Engineer (Cursor) → Architect

## 1. Summary

Delivered a **real finance-domain agentic graph** (`chorusgraph/examples/finance_agent/`) that runs the full ChorusGraph pipeline end-to-end: functional `cache_gate`, role-typed nodes (`ResearcherNode` / `WriterNode` / `ValidatorNode`), first-class `tool` node with live Frankfurter FX API, real **Gemini 2.5 Flash** drafting/validation, conversation state (`conversation_history`), and Route Ledger via `wrap()`.

This is **Container B** in embryo — function-first, no performance/cost measurement. The graph returns **correct answers** on real finance questions; a 2-turn demo shows turn 2 resolving a new currency pair while turn 3 demonstrates a **functional session cache hit** (tool skipped, ledger path shortened).

Package bumped to **v0.4.0**. **35 passed, 1 skipped** (`pytest -v`).

## 2. File tree

```
C:\code\ChorusGraph\
├── pyproject.toml                              # v0.4.0, httpx dep, gemini optional, chorusgraph-finance CLI
├── chorusgraph/
│   ├── __init__.py                             # v0.4.0
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── tool.py                             # ToolSpec, ToolRegistry, Frankfurter + compound_interest
│   │   └── roles.py                            # Node, Researcher/Writer/Validator, promote()
│   └── examples/
│       └── finance_agent/
│           ├── __init__.py
│           ├── gemini_client.py                # real Gemini (default gemini-2.5-flash)
│           ├── runtime.py                      # FinanceRuntime (cache, sidecar, registry)
│           ├── nodes.py                        # cache_gate, researcher, tool, writer, validator handlers
│           ├── graph.py                        # LangGraph assembly + FinanceState
│           └── run.py                          # 2-turn + cache-probe demo
├── tests/
│   ├── test_tool.py                            # real Frankfurter API
│   └── test_finance_agent.py                   # routing, cache seed, E2E (skip without GEMINI_API_KEY)
└── handoffs/
    └── handoffback4.md                         # this file
```

## 3. How to run

```powershell
cd C:\code\ChorusGraph
pip install -e ".[dev,gemini]"

# Set Gemini key (or place in .env / local env file read by resolve_gemini_api_key())
$env:GEMINI_API_KEY = "<your-key>"
# Optional: $env:GEMINI_MODEL = "gemini-2.5-flash"

pytest -v

# End-to-end finance demo (2-turn + cache probe)
python -m chorusgraph.examples.finance_agent.run
# or: chorusgraph-finance
```

## 4. Test results

```
================== 35 passed, 1 skipped, 1 warning in ~17s ==================
```

New tests: `test_tool.py` (3), `test_finance_agent.py` (5). E2E Gemini tests skip when `GEMINI_API_KEY` is unset.

## 5. Real end-to-end run output

```
=== Turn 1 ===
Question: What is the USD to EUR exchange rate today?
Answer: The USD to EUR exchange rate is 0.8785, as of 2026-07-01, according to frankfurter.app (ECB).
Tool calls: fetch_exchange_rate USD→EUR rate=0.8785 (Frankfurter, ok=true)
Cache hit: False
Validation: approved=true
Ledger path: cache_gate -> researcher -> tool -> writer -> validator
Rule chain: ['cache_gate=miss', 'researcher=fx_pair USD/EUR', 'tool=fetch_exchange_rate ok=True', 'writer=gemini_draft', 'validator approved=True']

=== Turn 2 ===
Question: What about USD to GBP?
Answer: The USD to GBP exchange rate is 0.75528 as of 2026-07-01, according to frankfurter.app (ECB).
Tool calls: fetch_exchange_rate USD→GBP rate=0.75528 (Frankfurter, ok=true)
Cache hit: False
Validation: approved=true
Ledger path: cache_gate -> researcher -> tool -> writer -> validator
Rule chain: ['cache_gate=miss', 'researcher=fx_pair USD/GBP', 'tool=fetch_exchange_rate ok=True', 'writer=gemini_draft', 'validator approved=True']

=== Turn 3 (cache probe — repeat turn-1 query, same runtime) ===
Question: What is the USD to EUR exchange rate today?
Answer: The USD to EUR exchange rate is 0.8785, as of 2026-07-01, according to frankfurter.app (ECB).
Tool calls: []   # tool skipped — cache_gate supplied tool_result
Cache hit: True (hit_revalidate)
Ledger path: cache_gate -> writer -> validator
Rule chain: ['cache_gate=hit_revalidate', 'writer=gemini_draft', 'validator approved=True']
```

Turn 2 uses `conversation_history` from turn 1; researcher prefers explicit currencies in the current message over merged prior context.

## 6. Decisions / deviations

| Decision | Rationale |
|----------|-----------|
| **Frankfurter API** (`fetch_exchange_rate`) | Free ECB reference FX data, no API key, real market rates via `httpx`. `compound_interest` also registered as deterministic calc tool. |
| **Researcher routing is deterministic** | FX pair detection + follow-up heuristics; role template attached for DESIGN §7.7 compliance. Gemini drives Writer + Validator rewrite path. |
| **Default model `gemini-2.5-flash`** | `gemini-2.0-flash` returns 404 (deprecated). Override via `GEMINI_MODEL`. Still uses `google-generativeai` (deprecated package — migrate to `google.genai` in H5). |
| **Cache thresholds 0.82 / 0.85** in finance graph | Slightly relaxed vs shadow defaults so functional session hits work after tool seeds user message. Not a measurement claim. |
| **Turn 3 cache probe in demo** | Proves functional cache within session without changing the 2-turn conversation narrative. |
| **No checkpointer** | Per handoff scope; `conversation_history` passed explicitly between invokes. |

## 7. Blockers

- **`google.generativeai` deprecation warning** — works today; should migrate to `google.genai` SDK.
- **Gemini E2E tests require key** — skip cleanly when unset; CI should inject `GEMINI_API_KEY` for full coverage.
- **Frankfurter via `urllib` got 403** in earlier probing — `httpx` with `follow_redirects=True` works reliably.

## 8. Answers to Handoff 4 §5

### 1. Which finance tool/data source, and why?

**Frankfurter** (`https://api.frankfurter.app`) for live FX rates — ECB reference data, no API key, deterministic JSON, suitable for reproducible functional demos. Secondary tool **`compound_interest`** for offline deterministic financial math.

### 2. Did the cache mechanically hit within a session?

**Yes.** After turn 1 seeds the cache with the user message + tool result, turn 3 (identical USD/EUR query) returns `cache_hit=True`, `cache_decision=hit_revalidate`, **skips researcher and tool**, and ledger shows `cache_gate -> writer -> validator`.

### 3. Awkwardness assembling pieces?

- **LangGraph node handlers vs role `Node` objects**: role nodes are callable `Node` instances bound with handlers — works but LangGraph expects plain callables; the indirection is slightly opaque.
- **Cache gate query vs tool seed key**: gate embeds the full user message; seeding must use the same message text (not just `USD/EUR` shorthand) for hits.
- **Follow-up currency parsing**: merging prior turn text before parsing caused EUR to win over GBP; fixed by parsing current message first.
- **Validator rate matching**: strict 4-decimal string compare missed rates like `0.75528`; fixed with tolerant numeric matching.
- **PrismCache sidecar still required** for Stage-2 verify — unchanged from H2.

### 4. Proposed H5 scope

1. **PrismCheckpointer + Cortex** — persist `conversation_history` and graph state across sessions (drop-in; state shape already thread-ready).
2. **Execution patterns** — ReAct / Reflection / Plan-Solve on top of role scaffold.
3. **Migrate Gemini client** to `google.genai`.
4. **HITL hooks** on `ValidatorNode` rejection path.
5. **A/B benchmark (Container B vs baseline)** — latency, cost, traffic, FP; out of scope for H4 by design.

## 9. Design contradictions

- DESIGN §7.7 implies Gemini drives all role nodes; H4 uses deterministic researcher routing for reliable tool selection while Gemini handles writer/validator — pragmatic split for a function-first milestone.
- `google.generativeai` is deprecated but was the fastest path to real Gemini; design should allow either SDK.
- Cache gate is wired functionally but not as live serve — consistent with ADR-002 shadow-only posture until benchmark blesses thresholds.

## 10. Acceptance criteria checklist

- [x] Finance graph runs end-to-end with correct answers (real Gemini)
- [x] `tool` node executes real Frankfurter API; result in final answer
- [x] `ValidatorNode` runs in graph (approval + rewrite path)
- [x] Conversation state; 2-turn demo uses turn-1 context
- [x] Route Ledger logs full path including tool call
- [x] No mocks/fakes; pytest green
- [x] No performance numbers reported

---
*Handoff 4 · architect: Claude · function-first · Container B finance graph · v0.4.0*
