# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Healthcare Multi (HL2 vs HC2)

**Overall:** langgraph (Chorus wins 2 metrics, LangGraph wins 9 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 52.5% [37.9%, 67.1%] | 82.5% [73.7%, 91.3%] | — |
| LLM calls / task | 3.88 [3.40, 4.35] | 3.90 [3.42, 4.38] | 0.0250 [0.0000, 0.0750] |
| Mean latency | 10559.92 [9017.47, 12153.59] | 12474.42 [10646.32, 14286.00] | 1914.50 [1121.89, 2668.83] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |
| Abstain rate | 7.5% [0.0%, 19.9%] | 5.0% [0.0%, 16.5%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 52.5% [37.9%, 67.1%] | 82.5% [73.7%, 91.3%] | — | **chorusgraph** |
| LLM calls / task | 3.88 [3.40, 4.35] | 3.90 [3.42, 4.38] | 0.0250 [0.0000, 0.0750] | **langgraph** |
| Mean latency | 10559.92 [9017.47, 12153.59] | 12474.42 [10646.32, 14286.00] | 1914.50 [1121.89, 2668.83] | **langgraph** |
| Latency p50 | 10866.50 [9595.50, 13587.50] | 14026.00 [10689.26, 15386.50] | — | **langgraph** |
| Latency p95 | 17862.45 [15323.25, 19812.00] | 21095.05 [18232.20, 23189.00] | — | **langgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0003 [0.0003, 0.0004] | 0.0000 [0.0000, 0.0001] | **langgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| LLM calls on cache hit | — | — | — | **inconclusive** |
| Tokens in / task | 873.40 [697.04, 1039.50] | 1126.88 [897.10, 1344.05] | — | **langgraph** |
| Tokens out / task | 301.35 [251.25, 350.26] | 289.50 [251.60, 328.13] | — | **chorusgraph** |
| Tool calls / task | 0.8500 [0.6250, 1.0750] | 0.9250 [0.6750, 1.1750] | — | **langgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 9.85 [8.88, 10.82] | — | **langgraph** |
| Abstain rate | 7.5% [0.0%, 19.9%] | 5.0% [0.0%, 16.5%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)
