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
| Mean latency | 5079.45 [4356.22, 5849.11] | 1548.45 [959.49, 2234.27] | -3531.0000 [-4190.8725, -2732.7400] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 87.5% [80.5%, 94.5%] | 100.0% [100.0%, 100.0%] | — | **chorusgraph** |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] | **chorusgraph** |
| Mean latency | 5079.45 [4356.22, 5849.11] | 1548.45 [959.49, 2234.27] | -3531.0000 [-4190.8725, -2732.7400] | **chorusgraph** |
| Latency p50 | 3993.00 [3831.00, 4174.00] | 55.00 [18.50, 2444.00] | — | **chorusgraph** |
| Latency p95 | 9381.10 [7929.30, 13724.00] | 5061.70 [2746.85, 8322.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1128.72 [995.74, 1269.63] | 336.20 [214.44, 470.00] | — | **chorusgraph** |
| Tokens out / task | 255.03 [224.52, 288.30] | 76.12 [48.12, 108.83] | — | **chorusgraph** |
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
| Task success | 75.0% [64.2%, 85.8%] | 87.5% [80.5%, 94.5%] | — |
| LLM calls / task | 2.05 [2.00, 2.12] | 0.8250 [0.5750, 1.0750] | -1.2250 [-1.4750, -0.9750] |
| Mean latency | 3264.82 [2688.50, 3945.83] | 1359.35 [886.88, 1892.81] | -1905.4750 [-2635.5906, -1278.2131] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 75.0% [64.2%, 85.8%] | 87.5% [80.5%, 94.5%] | — | **chorusgraph** |
| LLM calls / task | 2.05 [2.00, 2.12] | 0.8250 [0.5750, 1.0750] | -1.2250 [-1.4750, -0.9750] | **chorusgraph** |
| Mean latency | 3264.82 [2688.50, 3945.83] | 1359.35 [886.88, 1892.81] | -1905.4750 [-2635.5906, -1278.2131] | **chorusgraph** |
| Latency p50 | 2427.00 [2331.50, 2567.50] | 1146.00 [21.00, 1414.00] | — | **chorusgraph** |
| Latency p95 | 9094.55 [3732.50, 11016.00] | 4041.60 [2723.34, 6736.00] | — | **chorusgraph** |
| Cost / task | 0.0002 [0.0002, 0.0002] | 0.0001 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 579.80 [524.34, 636.38] | 252.65 [159.87, 358.64] | — | **chorusgraph** |
| Tokens out / task | 125.67 [117.42, 135.48] | 51.83 [37.40, 67.78] | — | **chorusgraph** |
| Tool calls / task | 0.9250 [0.8244, 1.0250] | 0.5250 [0.3500, 0.7000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 8.40 [7.80, 9.00] | — | **langgraph** |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** chorusgraph (Chorus wins 8 metrics, LangGraph wins 1 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 72.5% [61.1%, 83.9%] | 72.5% [61.1%, 83.9%] | — |
| LLM calls / task | 3.05 [2.77, 3.35] | 1.98 [1.65, 2.30] | -1.0750 [-1.5000, -0.7000] |
| Mean latency | 7699.90 [6314.47, 9227.03] | 5048.40 [4211.25, 5988.86] | -2651.5000 [-3873.8225, -1611.3763] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 42.5% [27.2%, 57.8%] | — |
| Abstain rate | 32.5% [17.0%, 48.0%] | 32.5% [17.0%, 48.0%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 72.5% [61.1%, 83.9%] | 72.5% [61.1%, 83.9%] | — | **tie** |
| LLM calls / task | 3.05 [2.77, 3.35] | 1.98 [1.65, 2.30] | -1.0750 [-1.5000, -0.7000] | **chorusgraph** |
| Mean latency | 7699.90 [6314.47, 9227.03] | 5048.40 [4211.25, 5988.86] | -2651.5000 [-3873.8225, -1611.3763] | **chorusgraph** |
| Latency p50 | 5868.50 [5492.00, 8432.00] | 3818.00 [3569.50, 5365.50] | — | **chorusgraph** |
| Latency p95 | 17198.40 [12018.00, 23705.00] | 12328.70 [6961.00, 12582.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0003 [0.0002, 0.0004] | -0.0000 [-0.0001, 0.0000] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 42.5% [27.2%, 57.8%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 962.35 [841.33, 1094.75] | 1216.72 [1000.18, 1458.55] | — | **langgraph** |
| Tokens out / task | 336.90 [299.40, 378.58] | 192.30 [146.47, 238.60] | — | **chorusgraph** |
| Tool calls / task | 1.38 [1.20, 1.60] | 0.7250 [0.5000, 0.9500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 32.5% [17.0%, 48.0%] | 32.5% [17.0%, 48.0%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** langgraph (Chorus wins 5 metrics, LangGraph wins 7 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 57.5% [43.5%, 71.5%] | 87.5% [80.5%, 94.5%] | — |
| LLM calls / task | 3.85 [3.38, 4.33] | 3.48 [3.00, 3.95] | -0.3750 [-0.6500, -0.1250] |
| Mean latency | 11149.70 [9509.83, 12785.79] | 11546.25 [9595.56, 13520.11] | 396.55 [-552.97, 1474.95] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 25.0% [9.8%, 40.2%] | — |
| Abstain rate | 10.0% [0.0%, 23.1%] | 5.0% [0.0%, 16.5%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 57.5% [43.5%, 71.5%] | 87.5% [80.5%, 94.5%] | — | **chorusgraph** |
| LLM calls / task | 3.85 [3.38, 4.33] | 3.48 [3.00, 3.95] | -0.3750 [-0.6500, -0.1250] | **chorusgraph** |
| Mean latency | 11149.70 [9509.83, 12785.79] | 11546.25 [9595.56, 13520.11] | 396.55 [-552.97, 1474.95] | **langgraph** |
| Latency p50 | 11670.00 [8806.50, 14660.50] | 12213.00 [7440.00, 14484.00] | — | **langgraph** |
| Latency p95 | 18682.60 [16670.95, 19912.00] | 21978.50 [17735.30, 27070.00] | — | **langgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0003 [0.0003, 0.0004] | 0.0000 [-0.0000, 0.0000] | **langgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 25.0% [9.8%, 40.2%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 2.50 [1.70, 3.30] | — | **inconclusive** |
| Tokens in / task | 895.17 [724.15, 1069.25] | 1063.42 [851.91, 1279.39] | — | **langgraph** |
| Tokens out / task | 316.57 [266.35, 367.85] | 281.57 [237.72, 325.80] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.7750 [0.5500, 1.0250] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 9.00 [8.02, 10.00] | — | **langgraph** |
| Abstain rate | 10.0% [0.0%, 23.1%] | 5.0% [0.0%, 16.5%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)
