# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 7 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | — |
| LLM calls / task | 5.00 [3.00, 7.00] | 2.00 [2.00, 2.00] | -3.0000 [-5.0000, -1.0000] |
| Mean latency | 6190.00 [3957.00, 8423.00] | 2575.50 [2411.00, 2740.00] | -3614.5000 [-5683.0000, -1546.0000] |
| Cache hit rate | 0.0% [0.0%, 65.8%] | 0.0% [0.0%, 65.8%] | — |
| Abstain rate | 0.0% [0.0%, 65.8%] | 0.0% [0.0%, 65.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | — | **tie** |
| LLM calls / task | 5.00 [3.00, 7.00] | 2.00 [2.00, 2.00] | -3.0000 [-5.0000, -1.0000] | **chorusgraph** |
| Mean latency | 6190.00 [3957.00, 8423.00] | 2575.50 [2411.00, 2740.00] | -3614.5000 [-5683.0000, -1546.0000] | **chorusgraph** |
| Latency p50 | 6190.00 [3957.00, 8423.00] | 2575.50 [2411.00, 2740.00] | — | **chorusgraph** |
| Latency p95 | 8199.70 [3957.00, 8423.00] | 2723.55 [2411.00, 2740.00] | — | **chorusgraph** |
| Cost / task | 0.0004 [0.0003, 0.0006] | 0.0002 [0.0001, 0.0002] | -0.0003 [-0.0005, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 65.8%] | 0.0% [0.0%, 65.8%] | — | **tie** |
| LLM calls on cache hit | — | — | — | **inconclusive** |
| Tokens in / task | 1655.00 [1007.00, 2303.00] | 637.00 [433.00, 841.00] | — | **chorusgraph** |
| Tokens out / task | 324.00 [228.00, 420.00] | 141.50 [103.00, 180.00] | — | **chorusgraph** |
| Tool calls / task | 0.5000 [0.0000, 1.0000] | 0.5000 [0.0000, 1.0000] | — | **tie** |
| Error rate | 0.0% [0.0%, 65.8%] | 0.0% [0.0%, 65.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 0.0% [0.0%, 65.8%] | 0.0% [0.0%, 65.8%] | — | **tie** |

Paired tasks: **2** (same task/case IDs)
