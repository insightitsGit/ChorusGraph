# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 3 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 50.0% [35.2%, 64.8%] | 47.5% [32.5%, 62.5%] | — |
| LLM calls / task | 3.80 [3.35, 4.25] | 2.58 [2.20, 2.98] | -1.2250 [-1.5500, -0.9000] |
| Mean latency | 10764.02 [9189.74, 12404.83] | 10331.52 [8646.80, 12070.73] | -432.5000 [-1529.4794, 641.7737] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — |
| Abstain rate | 15.0% [0.9%, 29.1%] | 17.5% [3.1%, 31.9%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 50.0% [35.2%, 64.8%] | 47.5% [32.5%, 62.5%] | — | **langgraph** |
| LLM calls / task | 3.80 [3.35, 4.25] | 2.58 [2.20, 2.98] | -1.2250 [-1.5500, -0.9000] | **chorusgraph** |
| Mean latency | 10764.02 [9189.74, 12404.83] | 10331.52 [8646.80, 12070.73] | -432.5000 [-1529.4794, 641.7737] | **chorusgraph** |
| Latency p50 | 11867.50 [8513.00, 14539.00] | 10698.50 [7383.00, 11918.00] | — | **chorusgraph** |
| Latency p95 | 17115.80 [16695.25, 19129.00] | 20787.45 [16424.00, 23525.00] | — | **langgraph** |
| Cost / task | 0.0003 [0.0002, 0.0003] | 0.0002 [0.0001, 0.0002] | -0.0001 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 2.35 [2.00, 2.69] | — | **inconclusive** |
| Tokens in / task | 837.42 [676.81, 997.51] | 428.07 [312.39, 553.51] | — | **chorusgraph** |
| Tokens out / task | 285.55 [243.14, 329.61] | 187.57 [157.52, 219.81] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.4000 [0.2250, 0.6000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 7.33 [6.55, 8.15] | — | **langgraph** |
| Abstain rate | 15.0% [0.9%, 29.1%] | 17.5% [3.1%, 31.9%] | — | **chorusgraph** |

Paired tasks: **40** (same task/case IDs)
