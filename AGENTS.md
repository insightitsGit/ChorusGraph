# Agent instructions (ChorusGraph repo)

## Terminology — read first

**“ChorusGraph” = full native product.** Engine, envelopes, cache, ledger, checkpoints, Prism stack.

**LangGraph is not ChorusGraph.** Use LangGraph only for FL*/HL* baseline scenarios and legacy `wrap()` migration.

Authoritative policy: [`docs/TERMINOLOGY.md`](docs/TERMINOLOGY.md)

## Before editing orchestration

| Task | Use |
|------|-----|
| FC1, FC2, HC1, HC2 benchmarks | `chorusgraph.core.Graph` + `ChorusStack.defaults()` |
| FL1, FL2, HL1, HL2 baselines | `langgraph.graph.StateGraph` |
| New product graphs | `docs/DEVELOPER_GUIDE.md` + `docs/COMPOSE.md` |
| Swap cache (Redis, etc.) | `ChorusStack.with_cache(RedisCacheBackend(...))` |

## Tests that enforce boundaries

- `tests/test_fc_hc_no_langgraph.py` — no `langgraph` imports on FC/HC paths

## Do not

- Add LangGraph to FC/HC code “temporarily” or as a shim
- Describe LangGraph+Prism hybrids as ChorusGraph in docs or reports
- Commit without user request (see user rules)
