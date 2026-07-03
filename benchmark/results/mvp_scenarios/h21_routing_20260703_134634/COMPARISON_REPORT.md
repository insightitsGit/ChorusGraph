# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 85.0% [77.1%, 92.9%] | 95.0% [91.4%, 98.6%] | — |
| LLM calls / task | 3.35 [2.98, 3.75] | 0.9250 [0.6000, 1.2500] | -2.4250 [-2.9000, -1.9500] |
| Mean latency | 5025.52 [4297.51, 5879.36] | 1508.85 [950.09, 2129.32] | -3516.6750 [-4248.8056, -2701.7350] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 85.0% [77.1%, 92.9%] | 95.0% [91.4%, 98.6%] | — | **chorusgraph** |
| LLM calls / task | 3.35 [2.98, 3.75] | 0.9250 [0.6000, 1.2500] | -2.4250 [-2.9000, -1.9500] | **chorusgraph** |
| Mean latency | 5025.52 [4297.51, 5879.36] | 1508.85 [950.09, 2129.32] | -3516.6750 [-4248.8056, -2701.7350] | **chorusgraph** |
| Latency p50 | 4188.00 [3862.50, 4614.50] | 21.00 [8.49, 2426.00] | — | **chorusgraph** |
| Latency p95 | 11989.85 [6545.20, 12939.00] | 5186.75 [2931.35, 6890.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1143.92 [1010.27, 1284.62] | 327.55 [205.27, 463.35] | — | **chorusgraph** |
| Tokens out / task | 260.82 [230.82, 293.03] | 79.38 [49.52, 113.31] | — | **chorusgraph** |
| Tool calls / task | 0.8250 [0.6750, 0.9750] | 0.3750 [0.2250, 0.5500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Finance Multi (FL2 vs FC2)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 2 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 75.0% [64.2%, 85.8%] | 85.0% [77.1%, 92.9%] | — |
| LLM calls / task | 2.02 [2.00, 2.08] | 0.8250 [0.5750, 1.0750] | -1.2000 [-1.4500, -0.9500] |
| Mean latency | 2910.78 [2569.93, 3297.16] | 1819.45 [1153.16, 2571.59] | -1091.3250 [-1817.5831, -304.0456] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 75.0% [64.2%, 85.8%] | 85.0% [77.1%, 92.9%] | — | **chorusgraph** |
| LLM calls / task | 2.02 [2.00, 2.08] | 0.8250 [0.5750, 1.0750] | -1.2000 [-1.4500, -0.9500] | **chorusgraph** |
| Mean latency | 2910.78 [2569.93, 3297.16] | 1819.45 [1153.16, 2571.59] | -1091.3250 [-1817.5831, -304.0456] | **chorusgraph** |
| Latency p50 | 2529.50 [2344.00, 2648.00] | 1301.00 [11.50, 1764.00] | — | **chorusgraph** |
| Latency p95 | 6408.35 [3364.00, 6687.00] | 6981.30 [3136.76, 8074.00] | — | **langgraph** |
| Cost / task | 0.0002 [0.0001, 0.0002] | 0.0001 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 558.27 [503.77, 616.18] | 201.07 [132.88, 274.41] | — | **chorusgraph** |
| Tokens out / task | 119.40 [112.00, 126.73] | 55.52 [39.70, 72.15] | — | **chorusgraph** |
| Tool calls / task | 0.9250 [0.8244, 1.0250] | 0.5250 [0.3500, 0.7000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 3.20 [2.90, 3.50] | — | **langgraph** |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 1 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 70.0% [58.1%, 81.9%] | 77.5% [67.3%, 87.7%] | — |
| LLM calls / task | 3.05 [2.77, 3.35] | 1.93 [1.57, 2.33] | -1.1250 [-1.5256, -0.7500] |
| Mean latency | 7458.80 [6117.82, 8991.51] | 5393.73 [4329.69, 6638.48] | -2065.0750 [-3152.7781, -1158.9244] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 50.0% [35.2%, 64.8%] | — |
| Abstain rate | 32.5% [17.0%, 48.0%] | 25.0% [9.8%, 40.2%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 70.0% [58.1%, 81.9%] | 77.5% [67.3%, 87.7%] | — | **chorusgraph** |
| LLM calls / task | 3.05 [2.77, 3.35] | 1.93 [1.57, 2.33] | -1.1250 [-1.5256, -0.7500] | **chorusgraph** |
| Mean latency | 7458.80 [6117.82, 8991.51] | 5393.73 [4329.69, 6638.48] | -2065.0750 [-3152.7781, -1158.9244] | **chorusgraph** |
| Latency p50 | 6031.00 [5118.50, 8776.50] | 3799.00 [3170.50, 5392.50] | — | **chorusgraph** |
| Latency p95 | 12703.50 [11300.05, 25569.00] | 11771.95 [8576.00, 21737.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0002 [0.0002, 0.0003] | -0.0001 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 50.0% [35.2%, 64.8%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 966.80 [844.05, 1098.69] | 599.50 [467.95, 753.59] | — | **chorusgraph** |
| Tokens out / task | 328.75 [294.80, 368.30] | 182.35 [131.74, 237.79] | — | **chorusgraph** |
| Tool calls / task | 1.38 [1.20, 1.60] | 0.6750 [0.4250, 0.9500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 32.5% [17.0%, 48.0%] | 25.0% [9.8%, 40.2%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 2 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 60.0% [46.3%, 73.7%] | 40.0% [24.6%, 55.4%] | — |
| LLM calls / task | 3.88 [3.40, 4.35] | 2.02 [1.73, 2.40] | -1.8500 [-2.4000, -1.3250] |
| Mean latency | 10355.48 [8698.99, 11954.34] | 7328.88 [6038.71, 8833.69] | -3026.6000 [-4579.1163, -1510.5081] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — |
| Abstain rate | 7.5% [0.0%, 19.9%] | 20.0% [5.2%, 34.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 60.0% [46.3%, 73.7%] | 40.0% [24.6%, 55.4%] | — | **langgraph** |
| LLM calls / task | 3.88 [3.40, 4.35] | 2.02 [1.73, 2.40] | -1.8500 [-2.4000, -1.3250] | **chorusgraph** |
| Mean latency | 10355.48 [8698.99, 11954.34] | 7328.88 [6038.71, 8833.69] | -3026.6000 [-4579.1163, -1510.5081] | **chorusgraph** |
| Latency p50 | 11335.00 [7694.00, 12959.50] | 5333.50 [4076.00, 9759.50] | — | **chorusgraph** |
| Latency p95 | 18991.15 [16292.00, 19854.00] | 16122.10 [11175.90, 19668.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0002] | -0.0002 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.62 [1.42, 1.81] | — | **inconclusive** |
| Tokens in / task | 882.65 [711.47, 1052.30] | 288.00 [218.07, 369.86] | — | **chorusgraph** |
| Tokens out / task | 297.88 [252.15, 344.00] | 161.18 [132.22, 192.71] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.1500 [0.0000, 0.3500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 2.02 [1.73, 2.40] | — | **langgraph** |
| Abstain rate | 7.5% [0.0%, 19.9%] | 20.0% [5.2%, 34.8%] | — | **chorusgraph** |

Paired tasks: **40** (same task/case IDs)
