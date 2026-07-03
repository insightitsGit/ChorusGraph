# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 90.0% [84.0%, 96.0%] | 100.0% [100.0%, 100.0%] | — |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] |
| Mean latency | 4807.15 [4188.81, 5475.07] | 1657.22 [967.35, 2548.47] | -3149.9250 [-3770.4969, -2489.0644] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 90.0% [84.0%, 96.0%] | 100.0% [100.0%, 100.0%] | — | **chorusgraph** |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] | **chorusgraph** |
| Mean latency | 4807.15 [4188.81, 5475.07] | 1657.22 [967.35, 2548.47] | -3149.9250 [-3770.4969, -2489.0644] | **chorusgraph** |
| Latency p50 | 4010.50 [3759.50, 4272.50] | 96.50 [27.00, 2375.00] | — | **chorusgraph** |
| Latency p95 | 9600.25 [8236.75, 10300.00] | 4839.00 [2746.00, 13491.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1144.25 [1009.86, 1283.01] | 335.82 [213.89, 468.88] | — | **chorusgraph** |
| Tokens out / task | 262.60 [229.37, 299.03] | 74.58 [47.45, 105.55] | — | **chorusgraph** |
| Tool calls / task | 0.8250 [0.6750, 0.9750] | 0.3750 [0.2250, 0.5500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Finance Multi (FL2 vs FC2)

**Overall:** inconclusive (Chorus wins 0 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|

Paired tasks: **0** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 1 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 75.0% [64.2%, 85.8%] | 72.5% [61.1%, 83.9%] | — |
| LLM calls / task | 3.05 [2.77, 3.35] | 1.93 [1.60, 2.25] | -1.1250 [-1.5250, -0.7750] |
| Mean latency | 6981.70 [5676.25, 8433.59] | 4748.25 [3859.18, 5704.18] | -2233.4500 [-3299.9538, -1294.1413] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 45.0% [29.8%, 60.2%] | — |
| Abstain rate | 30.0% [14.6%, 45.4%] | 30.0% [14.6%, 45.4%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 75.0% [64.2%, 85.8%] | 72.5% [61.1%, 83.9%] | — | **langgraph** |
| LLM calls / task | 3.05 [2.77, 3.35] | 1.93 [1.60, 2.25] | -1.1250 [-1.5250, -0.7750] | **chorusgraph** |
| Mean latency | 6981.70 [5676.25, 8433.59] | 4748.25 [3859.18, 5704.18] | -2233.4500 [-3299.9538, -1294.1413] | **chorusgraph** |
| Latency p50 | 5655.50 [4738.00, 6932.00] | 3562.50 [3046.00, 4797.00] | — | **chorusgraph** |
| Latency p95 | 16436.85 [10550.85, 22345.00] | 10886.80 [6902.68, 14120.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0002 [0.0002, 0.0002] | -0.0001 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 45.0% [29.8%, 60.2%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 952.92 [837.22, 1083.74] | 565.65 [460.09, 681.73] | — | **chorusgraph** |
| Tokens out / task | 328.88 [295.14, 369.16] | 181.97 [138.32, 225.95] | — | **chorusgraph** |
| Tool calls / task | 1.35 [1.18, 1.57] | 0.6750 [0.4500, 0.9000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 30.0% [14.6%, 45.4%] | 30.0% [14.6%, 45.4%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 2 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 65.0% [52.1%, 77.9%] | 55.0% [40.7%, 69.3%] | — |
| LLM calls / task | 3.83 [3.38, 4.28] | 2.02 [1.73, 2.40] | -1.8000 [-2.3500, -1.2750] |
| Mean latency | 9326.00 [7921.42, 10737.31] | 6967.23 [5814.01, 8264.23] | -2358.7750 [-3892.6781, -919.8563] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — |
| Abstain rate | 12.5% [0.0%, 26.1%] | 20.0% [5.2%, 34.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 65.0% [52.1%, 77.9%] | 55.0% [40.7%, 69.3%] | — | **langgraph** |
| LLM calls / task | 3.83 [3.38, 4.28] | 2.02 [1.73, 2.40] | -1.8000 [-2.3500, -1.2750] | **chorusgraph** |
| Mean latency | 9326.00 [7921.42, 10737.31] | 6967.23 [5814.01, 8264.23] | -2358.7750 [-3892.6781, -919.8563] | **chorusgraph** |
| Latency p50 | 10713.50 [7201.50, 12742.50] | 5697.00 [4762.71, 7235.00] | — | **chorusgraph** |
| Latency p95 | 15081.55 [14285.00, 16987.00] | 14375.30 [10796.65, 18011.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0002 [0.0001, 0.0002] | -0.0002 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.62 [1.42, 1.81] | — | **inconclusive** |
| Tokens in / task | 894.40 [719.17, 1075.43] | 298.30 [224.07, 391.61] | — | **chorusgraph** |
| Tokens out / task | 327.25 [270.02, 387.36] | 178.82 [147.10, 214.35] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.1500 [0.0000, 0.3500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 6.25 [5.65, 7.00] | — | **langgraph** |
| Abstain rate | 12.5% [0.0%, 26.1%] | 20.0% [5.2%, 34.8%] | — | **chorusgraph** |

Paired tasks: **40** (same task/case IDs)
