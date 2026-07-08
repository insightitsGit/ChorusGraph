# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 89.3% [86.2%, 92.3%] | 96.3% [94.7%, 97.9%] | — |
| LLM calls / task | 3.36 [3.22, 3.50] | 0.7867 [0.6800, 0.9000] | -2.5671 [-2.7315, -2.4060] |
| Mean latency | 5231.28 [4926.55, 5570.48] | 1374.79 [1168.14, 1593.54] | -3847.3624 [-4183.2045, -3544.2931] |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 49.7% [44.0%, 55.3%] | — |
| Abstain rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 89.3% [86.2%, 92.3%] | 96.3% [94.7%, 97.9%] | — | **chorusgraph** |
| LLM calls / task | 3.36 [3.22, 3.50] | 0.7867 [0.6800, 0.9000] | -2.5671 [-2.7315, -2.4060] | **chorusgraph** |
| Mean latency | 5231.28 [4926.55, 5570.48] | 1374.79 [1168.14, 1593.54] | -3847.3624 [-4183.2045, -3544.2931] | **chorusgraph** |
| Latency p50 | 4190.00 [4060.00, 4369.50] | 44.00 [37.00, 61.50] | — | **chorusgraph** |
| Latency p95 | 10602.85 [9406.41, 12477.00] | 6213.90 [4809.50, 6718.50] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0003 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 49.7% [44.0%, 55.3%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1181.46 [1132.94, 1231.90] | 281.11 [239.88, 326.29] | — | **chorusgraph** |
| Tokens out / task | 272.58 [260.02, 285.44] | 64.97 [55.55, 75.17] | — | **chorusgraph** |
| Tool calls / task | 0.8758 [0.8254, 0.9295] | 0.3567 [0.2967, 0.4167] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — | **tie** |

Paired tasks: **298** (same task/case IDs)

## Finance Multi (FL2 vs FC2)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 2 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 88.1% [84.4%, 91.7%] | 69.3% [64.4%, 74.3%] | — |
| LLM calls / task | 2.04 [2.02, 2.07] | 0.7533 [0.6833, 0.8233] | -1.3584 [-1.4469, -1.2611] |
| Mean latency | 3435.10 [3178.95, 3720.39] | 1233.89 [1080.32, 1391.52] | -2260.7168 [-2517.7737, -2014.6165] |
| Cache hit rate | 0.0% [0.0%, 1.7%] | 34.7% [29.1%, 40.2%] | — |
| Abstain rate | 0.0% [0.0%, 1.7%] | 0.0% [0.0%, 1.3%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 88.1% [84.4%, 91.7%] | 69.3% [64.4%, 74.3%] | — | **langgraph** |
| LLM calls / task | 2.04 [2.02, 2.07] | 0.7533 [0.6833, 0.8233] | -1.3584 [-1.4469, -1.2611] | **chorusgraph** |
| Mean latency | 3435.10 [3178.95, 3720.39] | 1233.89 [1080.32, 1391.52] | -2260.7168 [-2517.7737, -2014.6165] | **chorusgraph** |
| Latency p50 | 2533.50 [2429.00, 2618.00] | 1285.50 [1192.00, 1351.50] | — | **chorusgraph** |
| Latency p95 | 7233.00 [6441.25, 10210.00] | 3643.70 [2858.00, 5233.55] | — | **chorusgraph** |
| Cost / task | 0.0002 [0.0001, 0.0002] | 0.0001 [0.0001, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 1.7%] | 34.7% [29.1%, 40.2%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 555.22 [525.91, 585.14] | 170.67 [155.20, 185.84] | — | **chorusgraph** |
| Tokens out / task | 122.23 [116.78, 128.35] | 61.39 [55.68, 67.53] | — | **chorusgraph** |
| Tool calls / task | 0.9248 [0.8673, 0.9823] | 0.3233 [0.2700, 0.3833] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 1.7%] | 0.0% [0.0%, 1.3%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 7.36 [7.12, 7.62] | — | **langgraph** |
| Abstain rate | 0.0% [0.0%, 1.7%] | 0.0% [0.0%, 1.3%] | — | **tie** |

Paired tasks: **226** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 1 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 73.2% [68.5%, 77.9%] | 79.0% [74.8%, 83.2%] | — |
| LLM calls / task | 2.93 [2.83, 3.03] | 1.33 [1.26, 1.39] | -1.6020 [-1.7324, -1.4582] |
| Mean latency | 6815.95 [6399.22, 7299.67] | 3745.78 [3569.91, 3943.28] | -3076.4314 [-3504.1443, -2654.5627] |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 72.7% [67.9%, 77.4%] | — |
| Abstain rate | 33.4% [27.9%, 39.0%] | 23.3% [18.2%, 28.4%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 73.2% [68.5%, 77.9%] | 79.0% [74.8%, 83.2%] | — | **chorusgraph** |
| LLM calls / task | 2.93 [2.83, 3.03] | 1.33 [1.26, 1.39] | -1.6020 [-1.7324, -1.4582] | **chorusgraph** |
| Mean latency | 6815.95 [6399.22, 7299.67] | 3745.78 [3569.91, 3943.28] | -3076.4314 [-3504.1443, -2654.5627] | **chorusgraph** |
| Latency p50 | 5799.00 [5546.00, 6527.00] | 3293.00 [3178.47, 3470.52] | — | **chorusgraph** |
| Latency p95 | 14900.00 [11892.20, 16025.20] | 6063.25 [5579.00, 7959.05] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0003] | 0.0002 [0.0002, 0.0002] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 72.7% [67.9%, 77.4%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 888.01 [846.14, 933.16] | 876.80 [845.41, 911.12] | — | **chorusgraph** |
| Tokens out / task | 310.67 [298.78, 322.93] | 105.69 [94.45, 117.20] | — | **chorusgraph** |
| Tool calls / task | 1.26 [1.20, 1.33] | 0.2867 [0.2333, 0.3433] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 33.4% [27.9%, 39.0%] | 23.3% [18.2%, 28.4%] | — | **langgraph** |

Paired tasks: **299** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 8 metrics, LangGraph wins 4 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 63.9% [58.6%, 69.1%] | 74.3% [69.7%, 78.9%] | — |
| LLM calls / task | 3.82 [3.65, 3.99] | 2.67 [2.50, 2.84] | -1.1622 [-1.2601, -1.0676] |
| Mean latency | 10130.02 [9548.73, 10700.41] | 9833.84 [9177.56, 10473.05] | -333.6858 [-757.8554, 91.5091] |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 77.7% [73.3%, 82.0%] | — |
| Abstain rate | 15.5% [11.0%, 20.1%] | 4.3% [1.4%, 7.3%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 63.9% [58.6%, 69.1%] | 74.3% [69.7%, 78.9%] | — | **chorusgraph** |
| LLM calls / task | 3.82 [3.65, 3.99] | 2.67 [2.50, 2.84] | -1.1622 [-1.2601, -1.0676] | **chorusgraph** |
| Mean latency | 10130.02 [9548.73, 10700.41] | 9833.84 [9177.56, 10473.05] | -333.6858 [-757.8554, 91.5091] | **chorusgraph** |
| Latency p50 | 11024.00 [9834.00, 11884.04] | 10120.00 [8650.00, 10845.50] | — | **chorusgraph** |
| Latency p95 | 17035.00 [16636.00, 17945.75] | 18683.00 [17503.00, 19819.75] | — | **langgraph** |
| Cost / task | 0.0003 [0.0003, 0.0003] | 0.0002 [0.0002, 0.0003] | -0.0000 [-0.0001, -0.0000] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 77.7% [73.3%, 82.0%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 2.30 [2.14, 2.47] | — | **inconclusive** |
| Tokens in / task | 812.42 [753.26, 870.74] | 891.40 [825.23, 956.57] | — | **langgraph** |
| Tokens out / task | 281.47 [264.99, 297.52] | 190.24 [175.81, 205.32] | — | **chorusgraph** |
| Tool calls / task | 0.8716 [0.7905, 0.9527] | 0.4833 [0.4133, 0.5533] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 7.39 [7.06, 7.73] | — | **langgraph** |
| Abstain rate | 15.5% [11.0%, 20.1%] | 4.3% [1.4%, 7.3%] | — | **langgraph** |

Paired tasks: **296** (same task/case IDs)
