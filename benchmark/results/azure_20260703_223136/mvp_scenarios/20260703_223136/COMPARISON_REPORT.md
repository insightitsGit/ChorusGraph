# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 87.5% [80.5%, 94.5%] | 100.0% [100.0%, 100.0%] | — |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] |
| Mean latency | 4559.60 [3921.02, 5261.36] | 1680.35 [953.58, 2641.24] | -2879.2500 [-3617.8631, -2108.4150] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 87.5% [80.5%, 94.5%] | 100.0% [100.0%, 100.0%] | — | **chorusgraph** |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] | **chorusgraph** |
| Mean latency | 4559.60 [3921.02, 5261.36] | 1680.35 [953.58, 2641.24] | -2879.2500 [-3617.8631, -2108.4150] | **chorusgraph** |
| Latency p50 | 3657.00 [3499.00, 3865.50] | 68.00 [36.00, 2279.00] | — | **chorusgraph** |
| Latency p95 | 9507.50 [6995.75, 11149.00] | 5214.40 [2727.40, 15245.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1129.22 [995.86, 1270.43] | 335.25 [212.25, 468.78] | — | **chorusgraph** |
| Tokens out / task | 256.70 [226.17, 290.03] | 74.50 [47.40, 105.55] | — | **chorusgraph** |
| Tool calls / task | 0.8250 [0.6750, 0.9750] | 0.3750 [0.2250, 0.5500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Finance Multi (FL2 vs FC2)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 1 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 72.5% [61.1%, 83.9%] | 87.5% [80.5%, 94.5%] | — |
| LLM calls / task | 2.02 [2.00, 2.08] | 0.8250 [0.5750, 1.0750] | -1.2000 [-1.4500, -0.9500] |
| Mean latency | 3122.43 [2580.94, 3754.60] | 1432.85 [924.91, 1999.32] | -1689.5750 [-2326.3219, -1091.7775] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 72.5% [61.1%, 83.9%] | 87.5% [80.5%, 94.5%] | — | **chorusgraph** |
| LLM calls / task | 2.02 [2.00, 2.08] | 0.8250 [0.5750, 1.0750] | -1.2000 [-1.4500, -0.9500] | **chorusgraph** |
| Mean latency | 3122.43 [2580.94, 3754.60] | 1432.85 [924.91, 1999.32] | -1689.5750 [-2326.3219, -1091.7775] | **chorusgraph** |
| Latency p50 | 2384.00 [2240.50, 2649.50] | 1157.00 [45.95, 1343.50] | — | **chorusgraph** |
| Latency p95 | 6415.00 [3865.45, 10957.00] | 5078.70 [2996.00, 6842.00] | — | **chorusgraph** |
| Cost / task | 0.0002 [0.0001, 0.0002] | 0.0001 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 549.27 [494.92, 607.30] | 265.23 [164.98, 387.08] | — | **chorusgraph** |
| Tokens out / task | 115.75 [108.60, 123.75] | 56.80 [40.25, 75.25] | — | **chorusgraph** |
| Tool calls / task | 0.9250 [0.8244, 1.0250] | 0.5250 [0.3500, 0.7000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 8.40 [7.80, 9.00] | — | **langgraph** |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 1 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 75.0% [64.2%, 85.8%] | 80.0% [70.5%, 89.5%] | — |
| LLM calls / task | 3.10 [2.80, 3.42] | 1.88 [1.57, 2.23] | -1.2250 [-1.6500, -0.8500] |
| Mean latency | 7195.48 [5781.46, 8787.86] | 5135.23 [4156.36, 6245.24] | -2060.2500 [-3253.8194, -1039.3081] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 50.0% [35.2%, 64.8%] | — |
| Abstain rate | 30.0% [14.6%, 45.4%] | 25.0% [9.8%, 40.2%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 75.0% [64.2%, 85.8%] | 80.0% [70.5%, 89.5%] | — | **chorusgraph** |
| LLM calls / task | 3.10 [2.80, 3.42] | 1.88 [1.57, 2.23] | -1.2250 [-1.6500, -0.8500] | **chorusgraph** |
| Mean latency | 7195.48 [5781.46, 8787.86] | 5135.23 [4156.36, 6245.24] | -2060.2500 [-3253.8194, -1039.3081] | **chorusgraph** |
| Latency p50 | 5358.50 [4633.00, 7812.37] | 3637.00 [3340.50, 5168.50] | — | **chorusgraph** |
| Latency p95 | 15753.85 [11264.94, 25676.00] | 11903.10 [8040.00, 15844.00] | — | **chorusgraph** |
| Cost / task | 0.0004 [0.0003, 0.0004] | 0.0002 [0.0001, 0.0002] | -0.0002 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 50.0% [35.2%, 64.8%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 988.42 [858.55, 1131.18] | 550.05 [446.23, 670.51] | — | **chorusgraph** |
| Tokens out / task | 342.12 [303.30, 384.95] | 173.10 [128.99, 219.93] | — | **chorusgraph** |
| Tool calls / task | 1.40 [1.20, 1.62] | 0.6250 [0.4250, 0.8500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 30.0% [14.6%, 45.4%] | 25.0% [9.8%, 40.2%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 3 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 65.0% [52.1%, 77.9%] | 52.5% [37.9%, 67.1%] | — |
| LLM calls / task | 3.85 [3.38, 4.33] | 2.02 [1.70, 2.45] | -1.8250 [-2.3756, -1.3000] |
| Mean latency | 10549.73 [8914.25, 12199.40] | 7455.02 [6035.72, 9066.24] | -3094.7000 [-4930.4881, -1337.5513] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 67.5% [55.1%, 79.9%] | — |
| Abstain rate | 10.0% [0.0%, 23.1%] | 17.5% [3.1%, 31.9%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 65.0% [52.1%, 77.9%] | 52.5% [37.9%, 67.1%] | — | **langgraph** |
| LLM calls / task | 3.85 [3.38, 4.33] | 2.02 [1.70, 2.45] | -1.8250 [-2.3756, -1.3000] | **chorusgraph** |
| Mean latency | 10549.73 [8914.25, 12199.40] | 7455.02 [6035.72, 9066.24] | -3094.7000 [-4930.4881, -1337.5513] | **chorusgraph** |
| Latency p50 | 11566.00 [8367.50, 14204.00] | 6816.00 [4337.00, 8305.50] | — | **chorusgraph** |
| Latency p95 | 18457.05 [16279.10, 20829.00] | 18654.95 [11015.05, 22900.00] | — | **langgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0002] | -0.0002 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 67.5% [55.1%, 79.9%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.59 [1.41, 1.78] | — | **inconclusive** |
| Tokens in / task | 879.38 [703.47, 1047.53] | 303.07 [228.64, 386.08] | — | **chorusgraph** |
| Tokens out / task | 310.50 [259.87, 360.98] | 162.35 [135.22, 192.80] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.1500 [0.0000, 0.3500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 6.22 [5.60, 7.03] | — | **langgraph** |
| Abstain rate | 10.0% [0.0%, 23.1%] | 17.5% [3.1%, 31.9%] | — | **chorusgraph** |

Paired tasks: **40** (same task/case IDs)
