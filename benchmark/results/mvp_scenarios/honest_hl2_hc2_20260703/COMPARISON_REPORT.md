# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

> **Honest mode:** semantic cache disabled (`--no-cache`). Expect **0% cache hits** on C scenarios — failures reflect full LLM/tool paths.

## Healthcare Multi (HL2 vs HC2)

**Overall:** langgraph (Chorus wins 3 metrics, LangGraph wins 8 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 62.5% [49.2%, 75.8%] | 55.0% [40.7%, 69.3%] | — |
| LLM calls / task | 3.83 [3.35, 4.28] | 3.90 [3.40, 4.38] | 0.0750 [-0.0250, 0.1756] |
| Mean latency | 10015.92 [8659.86, 11360.99] | 11892.75 [10108.31, 13665.49] | 1876.83 [992.66, 2752.45] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |
| Abstain rate | 12.5% [0.0%, 26.1%] | 5.0% [0.0%, 16.5%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 62.5% [49.2%, 75.8%] | 55.0% [40.7%, 69.3%] | — | **langgraph** |
| LLM calls / task | 3.83 [3.35, 4.28] | 3.90 [3.40, 4.38] | 0.0750 [-0.0250, 0.1756] | **langgraph** |
| Mean latency | 10015.92 [8659.86, 11360.99] | 11892.75 [10108.31, 13665.49] | 1876.83 [992.66, 2752.45] | **langgraph** |
| Latency p50 | 11508.50 [7668.50, 12378.00] | 12760.50 [8675.00, 15767.50] | — | **langgraph** |
| Latency p95 | 16610.05 [14519.85, 18364.00] | 20492.05 [18457.25, 21935.00] | — | **langgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0003 [0.0002, 0.0003] | -0.0000 [-0.0000, 0.0000] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| LLM calls on cache hit | — | — | — | **inconclusive** |
| Tokens in / task | 799.90 [624.87, 965.87] | 744.62 [608.82, 874.23] | — | **chorusgraph** |
| Tokens out / task | 317.15 [264.42, 368.56] | 303.27 [260.77, 344.58] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.9500 [0.7000, 1.2000] | — | **langgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 3.90 [3.40, 4.38] | — | **langgraph** |
| Abstain rate | 12.5% [0.0%, 26.1%] | 5.0% [0.0%, 16.5%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)
