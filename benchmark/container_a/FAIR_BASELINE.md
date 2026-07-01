# Container A — Fair LangGraph Baseline

Container A is a **competent** LangGraph implementation of the finance agent used in the A/B
benchmark. It uses the same model, tools, and prompts as Container B; only the orchestration
framework differs.

## Architecture

```
START → react_agent ⇄ tool_executor → writer → validator → END
```

- **ReAct loop** — JSON `{thought, action, finish}` with up to 6 tool calls (standard pattern).
- **Tools** — shared `default_finance_registry()` (`fetch_exchange_rate`, `compound_interest`).
- **Model** — `gemini-2.5-flash` via the same `InstrumentedGeminiClient` wrapper (temperature 0.2
  writer / 0.0 JSON ReAct).
- **Prompts** — `benchmark/shared/prompts.py` (identical text to ChorusGraph role/ReAct prompts).
- **Checkpointer** — LangGraph `MemorySaver` for session thread continuity.
- **No** semantic cache, Cortex memory, Route Ledger, or ChorusGraph cache gate.

## Fair-baseline justification

| Choice | Why it's fair |
|--------|----------------|
| ReAct (not regex researcher) | LangGraph's idiomatic agent pattern; LLM selects tools like production LangGraph apps. Container B's base graph uses heuristic routing — A is not hobbled, B may have an advantage on simple FX pairs. |
| Same tool code | Frankfurter + compound_interest from `chorusgraph.nodes.tool` — identical I/O. |
| Same prompts | Shared module; no prompt engineering advantage for B. |
| MemorySaver checkpointer | Standard LangGraph session persistence; comparable to B's `conversation_history` state. |
| Writer + validator nodes | Mirrors B's post-tool synthesis and rate verification — not a single-shot ReAct answer. |
| No cache in A | Expected per BENCHMARK.md — cache is B's product feature, not a strawman omission. |

## Where a LangGraph expert might object

1. **ReAct vs deterministic researcher asymmetry** — B's default graph uses regex FX parsing (faster,
   fewer LLM calls on single-pair queries). A uses LLM ReAct every time. This favors B on latency/cost
   for simple queries; report must disclose it.
2. **Custom ReAct loop vs `create_react_agent`** — We use an explicit conditional-edge graph for
   transparent parity with B's observable writer/validator stages. `create_react_agent` would collapse
   those stages; our build is more comparable to B's multi-node graph.
3. **No LangGraph ToolNode prebuilt** — Manual tool dispatch matches B's `tool` node semantics
   (registry.run with retry metadata).

## Sign-off checklist

- [x] LangGraph checkpointer enabled
- [x] Standard ReAct JSON loop with tool catalog
- [x] Same Gemini model and temperatures as B
- [x] Same tools and prompts
- [x] No intentional capability removal beyond excluded B features (cache/Cortex/ledger)
