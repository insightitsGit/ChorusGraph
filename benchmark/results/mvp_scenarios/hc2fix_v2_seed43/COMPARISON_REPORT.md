# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Healthcare Multi (HL2 vs HC2)

**Overall:** langgraph (Chorus wins 5 metrics, LangGraph wins 7 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 57.5% [43.5%, 71.5%] | 92.5% [87.6%, 97.4%] | — |
| LLM calls / task | 3.88 [3.42, 4.35] | 3.60 [3.12, 4.10] | -0.2750 [-0.5250, -0.0500] |
| Mean latency | 10950.58 [9196.70, 12657.01] | 12234.55 [10236.69, 14232.58] | 1283.97 [135.45, 2482.10] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 20.0% [5.2%, 34.8%] | — |
| Abstain rate | 7.5% [0.0%, 19.9%] | 2.5% [0.0%, 12.9%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 57.5% [43.5%, 71.5%] | 92.5% [87.6%, 97.4%] | — | **chorusgraph** |
| LLM calls / task | 3.88 [3.42, 4.35] | 3.60 [3.12, 4.10] | -0.2750 [-0.5250, -0.0500] | **chorusgraph** |
| Mean latency | 10950.58 [9196.70, 12657.01] | 12234.55 [10236.69, 14232.58] | 1283.97 [135.45, 2482.10] | **langgraph** |
| Latency p50 | 12209.00 [8671.50, 14229.00] | 13276.00 [7213.00, 16716.00] | — | **langgraph** |
| Latency p95 | 18393.20 [16285.00, 22504.00] | 21600.50 [19326.06, 24275.00] | — | **langgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0003 [0.0003, 0.0004] | 0.0000 [-0.0000, 0.0000] | **langgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 20.0% [5.2%, 34.8%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 2.38 [1.50, 3.38] | — | **inconclusive** |
| Tokens in / task | 876.77 [699.35, 1051.95] | 1069.45 [850.49, 1280.86] | — | **langgraph** |
| Tokens out / task | 291.20 [239.92, 343.33] | 257.05 [220.72, 295.90] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.7750 [0.5500, 1.0000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 9.22 [8.25, 10.25] | — | **langgraph** |
| Abstain rate | 7.5% [0.0%, 19.9%] | 2.5% [0.0%, 12.9%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)
