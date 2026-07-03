# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 75.0% [64.2%, 85.8%] | 82.5% [73.7%, 91.3%] | — |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] |
| Mean latency | 4590.00 [3991.12, 5250.37] | 1526.83 [989.01, 2100.87] | -3063.1750 [-3604.1244, -2495.3400] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 75.0% [64.2%, 85.8%] | 82.5% [73.7%, 91.3%] | — | **chorusgraph** |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] | **chorusgraph** |
| Mean latency | 4590.00 [3991.12, 5250.37] | 1526.83 [989.01, 2100.87] | -3063.1750 [-3604.1244, -2495.3400] | **chorusgraph** |
| Latency p50 | 3757.00 [3592.47, 4044.00] | 28.00 [9.00, 2570.50] | — | **chorusgraph** |
| Latency p95 | 9326.20 [6700.95, 10750.00] | 4692.80 [3387.60, 5614.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1118.08 [982.94, 1258.16] | 335.90 [212.42, 470.16] | — | **chorusgraph** |
| Tokens out / task | 250.32 [221.47, 281.80] | 75.25 [48.10, 106.18] | — | **chorusgraph** |
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
| Task success | 67.5% [55.1%, 79.9%] | 85.0% [77.1%, 92.9%] | — |
| LLM calls / task | 2.08 [2.00, 2.17] | 0.6750 [0.4500, 0.9000] | -1.4000 [-1.6250, -1.1744] |
| Mean latency | 3504.90 [2818.49, 4242.25] | 1245.25 [775.04, 1751.34] | -2259.6500 [-3008.2331, -1531.6338] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 67.5% [55.1%, 79.9%] | 85.0% [77.1%, 92.9%] | — | **chorusgraph** |
| LLM calls / task | 2.08 [2.00, 2.17] | 0.6750 [0.4500, 0.9000] | -1.4000 [-1.6250, -1.1744] | **chorusgraph** |
| Mean latency | 3504.90 [2818.49, 4242.25] | 1245.25 [775.04, 1751.34] | -2259.6500 [-3008.2331, -1531.6338] | **chorusgraph** |
| Latency p50 | 2468.00 [2397.50, 2706.00] | 1352.00 [14.00, 1661.00] | — | **chorusgraph** |
| Latency p95 | 9146.40 [5100.00, 11105.00] | 4445.95 [2120.35, 7061.00] | — | **chorusgraph** |
| Cost / task | 0.0002 [0.0001, 0.0002] | 0.0000 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 560.00 [508.47, 612.18] | 151.65 [97.78, 210.91] | — | **chorusgraph** |
| Tokens out / task | 121.83 [112.42, 134.38] | 44.48 [30.02, 60.13] | — | **chorusgraph** |
| Tool calls / task | 0.9250 [0.8244, 1.0250] | 0.4500 [0.2750, 0.6250] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 3.05 [2.75, 3.35] | — | **langgraph** |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 1 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 75.0% [64.2%, 85.8%] | 72.5% [61.1%, 83.9%] | — |
| LLM calls / task | 3.00 [2.75, 3.25] | 1.93 [1.60, 2.25] | -1.0750 [-1.4750, -0.7250] |
| Mean latency | 6805.95 [5665.32, 8081.51] | 4717.73 [3798.20, 5719.10] | -2088.2250 [-3097.0287, -1245.0763] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 45.0% [29.8%, 60.2%] | — |
| Abstain rate | 30.0% [14.6%, 45.4%] | 30.0% [14.6%, 45.4%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 75.0% [64.2%, 85.8%] | 72.5% [61.1%, 83.9%] | — | **langgraph** |
| LLM calls / task | 3.00 [2.75, 3.25] | 1.93 [1.60, 2.25] | -1.0750 [-1.4750, -0.7250] | **chorusgraph** |
| Mean latency | 6805.95 [5665.32, 8081.51] | 4717.73 [3798.20, 5719.10] | -2088.2250 [-3097.0287, -1245.0763] | **chorusgraph** |
| Latency p50 | 5469.00 [4525.50, 7594.00] | 3357.50 [3123.00, 4697.50] | — | **chorusgraph** |
| Latency p95 | 13702.95 [10115.75, 17439.00] | 11497.80 [7545.00, 14862.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0002 [0.0002, 0.0002] | -0.0001 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 45.0% [29.8%, 60.2%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 924.38 [826.16, 1029.77] | 572.88 [465.84, 693.68] | — | **chorusgraph** |
| Tokens out / task | 318.80 [289.65, 351.56] | 182.50 [138.70, 227.18] | — | **chorusgraph** |
| Tool calls / task | 1.30 [1.15, 1.45] | 0.6750 [0.4500, 0.9000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 30.0% [14.6%, 45.4%] | 30.0% [14.6%, 45.4%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** langgraph (Chorus wins 4 metrics, LangGraph wins 6 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 57.5% [43.5%, 71.5%] | 42.5% [27.2%, 57.8%] | — |
| LLM calls / task | 3.88 [3.38, 4.35] | 3.88 [3.40, 4.35] | 0.0000 [-0.0750, 0.0750] |
| Mean latency | 10553.27 [8987.96, 12215.27] | 12464.95 [10584.58, 14300.78] | 1911.67 [905.67, 2935.85] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 62.5% [49.2%, 75.8%] | — |
| Abstain rate | 7.5% [0.0%, 19.9%] | 7.5% [0.0%, 19.9%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 57.5% [43.5%, 71.5%] | 42.5% [27.2%, 57.8%] | — | **langgraph** |
| LLM calls / task | 3.88 [3.38, 4.35] | 3.88 [3.40, 4.35] | 0.0000 [-0.0750, 0.0750] | **tie** |
| Mean latency | 10553.27 [8987.96, 12215.27] | 12464.95 [10584.58, 14300.78] | 1911.67 [905.67, 2935.85] | **langgraph** |
| Latency p50 | 11141.50 [7959.50, 12912.00] | 12782.00 [9217.00, 16519.50] | — | **langgraph** |
| Latency p95 | 18444.80 [15954.00, 21318.00] | 20945.65 [19359.95, 22629.00] | — | **langgraph** |
| Cost / task | 0.0003 [0.0002, 0.0004] | 0.0003 [0.0002, 0.0003] | -0.0000 [-0.0001, 0.0000] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 62.5% [49.2%, 75.8%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 4.48 [3.96, 4.96] | — | **inconclusive** |
| Tokens in / task | 809.77 [632.20, 982.79] | 637.52 [505.86, 765.33] | — | **chorusgraph** |
| Tokens out / task | 305.93 [248.57, 364.05] | 293.45 [252.82, 333.80] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.9500 [0.7000, 1.2000] | — | **langgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 3.88 [3.40, 4.35] | — | **langgraph** |
| Abstain rate | 7.5% [0.0%, 19.9%] | 7.5% [0.0%, 19.9%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)
