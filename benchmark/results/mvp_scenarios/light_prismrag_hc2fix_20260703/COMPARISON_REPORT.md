# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 2 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 60.0% [46.3%, 73.7%] | 45.0% [29.8%, 60.2%] | — |
| LLM calls / task | 3.83 [3.38, 4.28] | 2.02 [1.73, 2.40] | -1.8000 [-2.3500, -1.2750] |
| Mean latency | 8770.00 [7478.19, 10021.64] | 6641.12 [5494.90, 7883.29] | -2128.8750 [-3368.8587, -961.0138] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — |
| Abstain rate | 12.5% [0.0%, 26.1%] | 20.0% [5.2%, 34.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 60.0% [46.3%, 73.7%] | 45.0% [29.8%, 60.2%] | — | **langgraph** |
| LLM calls / task | 3.83 [3.38, 4.28] | 2.02 [1.73, 2.40] | -1.8000 [-2.3500, -1.2750] | **chorusgraph** |
| Mean latency | 8770.00 [7478.19, 10021.64] | 6641.12 [5494.90, 7883.29] | -2128.8750 [-3368.8587, -961.0138] | **chorusgraph** |
| Latency p50 | 9056.50 [7183.00, 11455.00] | 4857.50 [3822.00, 8465.00] | — | **chorusgraph** |
| Latency p95 | 14327.15 [12940.40, 16223.00] | 12936.85 [10150.30, 17411.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0002, 0.0003] | 0.0001 [0.0001, 0.0002] | -0.0001 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.62 [1.42, 1.81] | — | **inconclusive** |
| Tokens in / task | 831.65 [667.75, 990.94] | 327.45 [235.32, 436.70] | — | **chorusgraph** |
| Tokens out / task | 276.68 [237.17, 316.60] | 153.93 [121.46, 190.10] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.1500 [0.0000, 0.3500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 6.25 [5.65, 7.00] | — | **langgraph** |
| Abstain rate | 12.5% [0.0%, 26.1%] | 20.0% [5.2%, 34.8%] | — | **chorusgraph** |

Paired tasks: **40** (same task/case IDs)
