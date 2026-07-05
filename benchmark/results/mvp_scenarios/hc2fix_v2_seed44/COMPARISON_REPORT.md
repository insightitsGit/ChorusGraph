# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Healthcare Multi (HL2 vs HC2)

**Overall:** langgraph (Chorus wins 5 metrics, LangGraph wins 7 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 50.0% [35.2%, 64.8%] | 77.5% [67.3%, 87.7%] | — |
| LLM calls / task | 3.83 [3.38, 4.28] | 3.40 [3.02, 3.80] | -0.4250 [-0.7000, -0.2000] |
| Mean latency | 10864.52 [9138.58, 12693.79] | 11632.17 [10043.15, 13291.01] | 767.65 [-396.70, 1770.64] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 25.0% [9.8%, 40.2%] | — |
| Abstain rate | 12.5% [0.0%, 26.1%] | 7.5% [0.0%, 19.9%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 50.0% [35.2%, 64.8%] | 77.5% [67.3%, 87.7%] | — | **chorusgraph** |
| LLM calls / task | 3.83 [3.38, 4.28] | 3.40 [3.02, 3.80] | -0.4250 [-0.7000, -0.2000] | **chorusgraph** |
| Mean latency | 10864.52 [9138.58, 12693.79] | 11632.17 [10043.15, 13291.01] | 767.65 [-396.70, 1770.64] | **langgraph** |
| Latency p50 | 11253.50 [7675.50, 13674.47] | 12564.00 [9250.83, 14289.50] | — | **langgraph** |
| Latency p95 | 18367.80 [17216.30, 23869.00] | 19580.70 [17439.10, 22339.00] | — | **langgraph** |
| Cost / task | 0.0003 [0.0002, 0.0003] | 0.0003 [0.0003, 0.0003] | 0.0000 [-0.0000, 0.0000] | **langgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 25.0% [9.8%, 40.2%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 3.40 [2.70, 4.00] | — | **inconclusive** |
| Tokens in / task | 831.48 [671.20, 986.65] | 1010.17 [804.81, 1212.23] | — | **langgraph** |
| Tokens out / task | 276.15 [235.42, 317.86] | 249.97 [216.80, 282.35] | — | **chorusgraph** |
| Tool calls / task | 0.8500 [0.6250, 1.0750] | 0.7250 [0.5250, 0.9500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 8.88 [8.10, 9.68] | — | **langgraph** |
| Abstain rate | 12.5% [0.0%, 26.1%] | 7.5% [0.0%, 19.9%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)
