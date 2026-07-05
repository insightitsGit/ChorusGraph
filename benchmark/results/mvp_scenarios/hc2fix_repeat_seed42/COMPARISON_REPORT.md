# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Healthcare Multi (HL2 vs HC2)

**Overall:** langgraph (Chorus wins 2 metrics, LangGraph wins 9 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 62.5% [49.2%, 75.8%] | 90.0% [84.0%, 96.0%] | — |
| LLM calls / task | 3.85 [3.38, 4.33] | 3.95 [3.45, 4.45] | 0.1000 [0.0250, 0.2000] |
| Mean latency | 10834.60 [9214.20, 12507.17] | 13143.45 [10662.88, 15928.69] | 2308.85 [833.27, 4215.08] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |
| Abstain rate | 10.0% [0.0%, 23.1%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 62.5% [49.2%, 75.8%] | 90.0% [84.0%, 96.0%] | — | **chorusgraph** |
| LLM calls / task | 3.85 [3.38, 4.33] | 3.95 [3.45, 4.45] | 0.1000 [0.0250, 0.2000] | **langgraph** |
| Mean latency | 10834.60 [9214.20, 12507.17] | 13143.45 [10662.88, 15928.69] | 2308.85 [833.27, 4215.08] | **langgraph** |
| Latency p50 | 12147.50 [9191.00, 14203.00] | 13334.50 [10430.00, 15532.00] | — | **langgraph** |
| Latency p95 | 17706.10 [16492.90, 22345.00] | 21816.30 [18596.00, 51729.00] | — | **langgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0004 [0.0003, 0.0004] | 0.0000 [0.0000, 0.0001] | **langgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| LLM calls on cache hit | — | — | — | **inconclusive** |
| Tokens in / task | 872.70 [701.21, 1046.73] | 1156.83 [924.43, 1387.58] | — | **langgraph** |
| Tokens out / task | 299.23 [253.40, 347.18] | 296.02 [257.15, 333.75] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.9500 [0.7000, 1.2000] | — | **langgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 9.90 [8.90, 10.90] | — | **langgraph** |
| Abstain rate | 10.0% [0.0%, 23.1%] | 0.0% [0.0%, 8.8%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)
