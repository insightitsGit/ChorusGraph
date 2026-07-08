# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 82.5% [73.7%, 91.3%] | 100.0% [100.0%, 100.0%] | — |
| LLM calls / task | 3.35 [2.98, 3.75] | 0.9250 [0.6000, 1.2500] | -2.4250 [-2.9000, -1.9500] |
| Mean latency | 4949.30 [4173.92, 5872.90] | 1393.05 [872.44, 1969.01] | -3556.2500 [-4347.8881, -2814.7775] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 82.5% [73.7%, 91.3%] | 100.0% [100.0%, 100.0%] | — | **chorusgraph** |
| LLM calls / task | 3.35 [2.98, 3.75] | 0.9250 [0.6000, 1.2500] | -2.4250 [-2.9000, -1.9500] | **chorusgraph** |
| Mean latency | 4949.30 [4173.92, 5872.90] | 1393.05 [872.44, 1969.01] | -3556.2500 [-4347.8881, -2814.7775] | **chorusgraph** |
| Latency p50 | 3811.00 [3602.00, 4240.00] | 43.50 [23.00, 2409.00] | — | **chorusgraph** |
| Latency p95 | 12123.30 [7724.00, 14083.00] | 4717.65 [2653.65, 6698.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1149.22 [1015.52, 1291.21] | 333.88 [211.12, 469.34] | — | **chorusgraph** |
| Tokens out / task | 254.72 [227.02, 285.05] | 72.95 [46.42, 103.73] | — | **chorusgraph** |
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
| Task success | 90.0% [84.0%, 96.0%] | 95.0% [91.4%, 98.6%] | — |
| LLM calls / task | 2.08 [2.00, 2.17] | 0.7000 [0.5000, 0.9000] | -1.3750 [-1.5750, -1.1500] |
| Mean latency | 3113.50 [2517.01, 3819.94] | 1015.62 [680.72, 1382.82] | -2097.8750 [-2729.5281, -1550.6806] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 90.0% [84.0%, 96.0%] | 95.0% [91.4%, 98.6%] | — | **chorusgraph** |
| LLM calls / task | 2.08 [2.00, 2.17] | 0.7000 [0.5000, 0.9000] | -1.3750 [-1.5750, -1.1500] | **chorusgraph** |
| Mean latency | 3113.50 [2517.01, 3819.94] | 1015.62 [680.72, 1382.82] | -2097.8750 [-2729.5281, -1550.6806] | **chorusgraph** |
| Latency p50 | 2355.50 [2216.50, 2457.50] | 1150.00 [13.00, 1305.01] | — | **chorusgraph** |
| Latency p95 | 8524.35 [3265.25, 11178.00] | 2447.75 [1629.85, 5195.00] | — | **chorusgraph** |
| Cost / task | 0.0002 [0.0002, 0.0002] | 0.0001 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 585.75 [527.17, 644.95] | 157.95 [115.32, 201.55] | — | **chorusgraph** |
| Tokens out / task | 124.50 [116.20, 134.80] | 52.02 [37.80, 67.20] | — | **chorusgraph** |
| Tool calls / task | 0.9250 [0.8244, 1.0250] | 0.5250 [0.3500, 0.7000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 8.40 [7.80, 9.00] | — | **langgraph** |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 1 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 70.0% [58.1%, 81.9%] | 70.0% [58.1%, 81.9%] | — |
| LLM calls / task | 3.08 [2.80, 3.38] | 1.95 [1.65, 2.27] | -1.1250 [-1.5250, -0.7750] |
| Mean latency | 7308.52 [6034.10, 8762.28] | 4627.05 [3879.22, 5467.23] | -2681.4750 [-3818.4394, -1718.9706] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 42.5% [27.2%, 57.8%] | — |
| Abstain rate | 30.0% [14.6%, 45.4%] | 32.5% [17.0%, 48.0%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 70.0% [58.1%, 81.9%] | 70.0% [58.1%, 81.9%] | — | **tie** |
| LLM calls / task | 3.08 [2.80, 3.38] | 1.95 [1.65, 2.27] | -1.1250 [-1.5250, -0.7750] | **chorusgraph** |
| Mean latency | 7308.52 [6034.10, 8762.28] | 4627.05 [3879.22, 5467.23] | -2681.4750 [-3818.4394, -1718.9706] | **chorusgraph** |
| Latency p50 | 6004.50 [5133.00, 8383.00] | 3549.00 [3216.50, 4162.50] | — | **chorusgraph** |
| Latency p95 | 12197.65 [11353.80, 23235.00] | 10938.95 [6532.32, 11896.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0003 [0.0002, 0.0003] | -0.0001 [-0.0001, -0.0000] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 42.5% [27.2%, 57.8%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 971.88 [851.27, 1101.38] | 1174.75 [970.74, 1410.23] | — | **langgraph** |
| Tokens out / task | 331.02 [295.87, 370.66] | 191.05 [147.09, 235.40] | — | **chorusgraph** |
| Tool calls / task | 1.38 [1.20, 1.60] | 0.7000 [0.4750, 0.9250] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 30.0% [14.6%, 45.4%] | 32.5% [17.0%, 48.0%] | — | **chorusgraph** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** langgraph (Chorus wins 5 metrics, LangGraph wins 7 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 57.5% [43.5%, 71.5%] | 90.0% [84.0%, 96.0%] | — |
| LLM calls / task | 3.83 [3.35, 4.28] | 3.50 [3.00, 4.00] | -0.3250 [-0.6000, -0.0750] |
| Mean latency | 10476.55 [8985.97, 11972.48] | 10854.23 [9087.80, 12629.07] | 377.68 [-372.53, 1176.95] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 25.0% [9.8%, 40.2%] | — |
| Abstain rate | 12.5% [0.0%, 26.1%] | 2.5% [0.0%, 12.9%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 57.5% [43.5%, 71.5%] | 90.0% [84.0%, 96.0%] | — | **chorusgraph** |
| LLM calls / task | 3.83 [3.35, 4.28] | 3.50 [3.00, 4.00] | -0.3250 [-0.6000, -0.0750] | **chorusgraph** |
| Mean latency | 10476.55 [8985.97, 11972.48] | 10854.23 [9087.80, 12629.07] | 377.68 [-372.53, 1176.95] | **langgraph** |
| Latency p50 | 11534.00 [9663.00, 13449.50] | 11722.00 [7919.00, 14023.50] | — | **langgraph** |
| Latency p95 | 16390.75 [15539.90, 19467.00] | 18347.90 [17380.00, 21351.00] | — | **langgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0003 [0.0003, 0.0004] | 0.0000 [-0.0000, 0.0000] | **langgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 25.0% [9.8%, 40.2%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 2.50 [1.70, 3.30] | — | **inconclusive** |
| Tokens in / task | 858.27 [693.78, 1024.96] | 1051.15 [834.86, 1267.48] | — | **langgraph** |
| Tokens out / task | 295.27 [251.67, 340.00] | 265.07 [221.15, 310.13] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.7750 [0.5500, 1.0250] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 9.03 [8.03, 10.03] | — | **langgraph** |
| Abstain rate | 12.5% [0.0%, 26.1%] | 2.5% [0.0%, 12.9%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)
