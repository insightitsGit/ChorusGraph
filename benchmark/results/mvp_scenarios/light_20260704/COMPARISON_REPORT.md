# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 87.5% [80.5%, 94.5%] | 95.0% [91.4%, 98.6%] | — |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] |
| Mean latency | 4758.05 [4134.42, 5458.49] | 1568.67 [958.35, 2268.19] | -3189.3750 [-3719.8369, -2627.4038] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 87.5% [80.5%, 94.5%] | 95.0% [91.4%, 98.6%] | — | **chorusgraph** |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] | **chorusgraph** |
| Mean latency | 4758.05 [4134.42, 5458.49] | 1568.67 [958.35, 2268.19] | -3189.3750 [-3719.8369, -2627.4038] | **chorusgraph** |
| Latency p50 | 3646.00 [3573.00, 4190.00] | 15.50 [6.00, 2364.00] | — | **chorusgraph** |
| Latency p95 | 8787.95 [7170.25, 12886.00] | 6459.70 [2850.40, 8012.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1147.42 [1014.59, 1288.10] | 328.65 [206.37, 464.55] | — | **chorusgraph** |
| Tokens out / task | 260.18 [230.77, 291.88] | 76.60 [48.55, 109.33] | — | **chorusgraph** |
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
| Task success | 75.0% [64.2%, 85.8%] | 85.0% [77.1%, 92.9%] | — |
| LLM calls / task | 2.05 [2.00, 2.12] | 0.8250 [0.5750, 1.0750] | -1.2250 [-1.4750, -0.9750] |
| Mean latency | 3148.53 [2687.96, 3711.08] | 1443.85 [975.83, 1945.47] | -1704.6750 [-2369.1094, -1065.8906] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 75.0% [64.2%, 85.8%] | 85.0% [77.1%, 92.9%] | — | **chorusgraph** |
| LLM calls / task | 2.05 [2.00, 2.12] | 0.8250 [0.5750, 1.0750] | -1.2250 [-1.4750, -0.9750] | **chorusgraph** |
| Mean latency | 3148.53 [2687.96, 3711.08] | 1443.85 [975.83, 1945.47] | -1704.6750 [-2369.1094, -1065.8906] | **chorusgraph** |
| Latency p50 | 2538.50 [2350.00, 2775.50] | 1262.00 [9.00, 1768.50] | — | **chorusgraph** |
| Latency p95 | 6494.75 [3527.00, 9375.00] | 4436.55 [2753.00, 6619.00] | — | **chorusgraph** |
| Cost / task | 0.0002 [0.0001, 0.0002] | 0.0001 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 566.05 [511.06, 623.88] | 251.68 [159.07, 365.68] | — | **chorusgraph** |
| Tokens out / task | 122.75 [114.07, 133.90] | 57.05 [40.37, 74.53] | — | **chorusgraph** |
| Tool calls / task | 0.9250 [0.8244, 1.0250] | 0.5250 [0.3500, 0.7000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 8.40 [7.80, 9.00] | — | **langgraph** |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 2 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 75.0% [64.2%, 85.8%] | 77.5% [67.3%, 87.7%] | — |
| LLM calls / task | 2.98 [2.75, 3.23] | 1.88 [1.57, 2.23] | -1.1000 [-1.4756, -0.7500] |
| Mean latency | 6411.07 [5441.75, 7440.47] | 4184.12 [3512.69, 4958.83] | -2226.9500 [-3066.2912, -1471.5188] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 50.0% [35.2%, 64.8%] | — |
| Abstain rate | 30.0% [14.6%, 45.4%] | 25.0% [9.8%, 40.2%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 75.0% [64.2%, 85.8%] | 77.5% [67.3%, 87.7%] | — | **chorusgraph** |
| LLM calls / task | 2.98 [2.75, 3.23] | 1.88 [1.57, 2.23] | -1.1000 [-1.4756, -0.7500] | **chorusgraph** |
| Mean latency | 6411.07 [5441.75, 7440.47] | 4184.12 [3512.69, 4958.83] | -2226.9500 [-3066.2912, -1471.5188] | **chorusgraph** |
| Latency p50 | 5190.50 [4744.79, 7614.00] | 3223.50 [3018.00, 4037.00] | — | **chorusgraph** |
| Latency p95 | 11328.70 [10517.00, 14519.00] | 8579.45 [6047.00, 12370.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0003 [0.0002, 0.0003] | -0.0000 [-0.0001, 0.0000] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 50.0% [35.2%, 64.8%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 913.55 [813.85, 1021.16] | 1205.78 [1009.42, 1432.69] | — | **langgraph** |
| Tokens out / task | 313.50 [287.57, 342.33] | 177.35 [133.87, 225.40] | — | **chorusgraph** |
| Tool calls / task | 1.27 [1.12, 1.43] | 0.6250 [0.4250, 0.8500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 30.0% [14.6%, 45.4%] | 25.0% [9.8%, 40.2%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 2 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 60.0% [46.3%, 73.7%] | 45.0% [29.8%, 60.2%] | — |
| LLM calls / task | 3.83 [3.35, 4.28] | 2.02 [1.73, 2.40] | -1.8000 [-2.3500, -1.2750] |
| Mean latency | 10087.17 [8583.64, 11600.31] | 6790.95 [5634.07, 8038.64] | -3296.2250 [-4751.9956, -1947.6006] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — |
| Abstain rate | 12.5% [0.0%, 26.1%] | 20.0% [5.2%, 34.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 60.0% [46.3%, 73.7%] | 45.0% [29.8%, 60.2%] | — | **langgraph** |
| LLM calls / task | 3.83 [3.35, 4.28] | 2.02 [1.73, 2.40] | -1.8000 [-2.3500, -1.2750] | **chorusgraph** |
| Mean latency | 10087.17 [8583.64, 11600.31] | 6790.95 [5634.07, 8038.64] | -3296.2250 [-4751.9956, -1947.6006] | **chorusgraph** |
| Latency p50 | 10560.00 [9178.00, 13943.00] | 5186.00 [4164.50, 8258.00] | — | **chorusgraph** |
| Latency p95 | 15976.40 [15349.00, 19737.00] | 13842.95 [11159.12, 17864.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0002 [0.0001, 0.0002] | -0.0001 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.62 [1.42, 1.81] | — | **inconclusive** |
| Tokens in / task | 865.12 [686.80, 1036.68] | 331.18 [238.94, 436.45] | — | **chorusgraph** |
| Tokens out / task | 298.90 [250.94, 349.15] | 182.62 [141.02, 228.08] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.1500 [0.0000, 0.3500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 6.25 [5.65, 7.00] | — | **langgraph** |
| Abstain rate | 12.5% [0.0%, 26.1%] | 20.0% [5.2%, 34.8%] | — | **chorusgraph** |

Paired tasks: **40** (same task/case IDs)
