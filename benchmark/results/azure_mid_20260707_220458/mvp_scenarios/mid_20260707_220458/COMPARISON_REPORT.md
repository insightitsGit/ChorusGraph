# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 93.9% [90.7%, 97.2%] | 99.0% [98.2%, 99.8%] | — |
| LLM calls / task | 3.24 [3.03, 3.48] | 0.7500 [0.5600, 0.9500] | -2.4848 [-2.7677, -2.2020] |
| Mean latency | 4702.10 [4329.63, 5092.14] | 1235.88 [896.28, 1625.88] | -3453.8788 [-3863.1561, -3011.1179] |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 53.0% [43.5%, 62.5%] | — |
| Abstain rate | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 93.9% [90.7%, 97.2%] | 99.0% [98.2%, 99.8%] | — | **chorusgraph** |
| LLM calls / task | 3.24 [3.03, 3.48] | 0.7500 [0.5600, 0.9500] | -2.4848 [-2.7677, -2.2020] | **chorusgraph** |
| Mean latency | 4702.10 [4329.63, 5092.14] | 1235.88 [896.28, 1625.88] | -3453.8788 [-3863.1561, -3011.1179] | **chorusgraph** |
| Latency p50 | 4027.00 [3763.60, 4283.00] | 30.50 [24.00, 142.15] | — | **chorusgraph** |
| Latency p95 | 8692.20 [7543.10, 9288.90] | 5174.20 [2975.15, 6301.50] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0003] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 53.0% [43.5%, 62.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1126.25 [1048.21, 1204.79] | 262.45 [191.46, 333.23] | — | **chorusgraph** |
| Tokens out / task | 254.37 [236.88, 273.68] | 60.58 [43.81, 78.01] | — | **chorusgraph** |
| Tool calls / task | 0.8283 [0.7475, 0.8990] | 0.3100 [0.2200, 0.4100] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] | — | **tie** |

Paired tasks: **99** (same task/case IDs)

## Finance Multi (FL2 vs FC2)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 2 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 89.9% [85.0%, 94.8%] | 74.0% [66.4%, 81.6%] | — |
| LLM calls / task | 2.04 [2.00, 2.09] | 0.6900 [0.5700, 0.8200] | -1.4177 [-1.5696, -1.2532] |
| Mean latency | 3335.01 [2881.46, 3848.95] | 1058.54 [815.13, 1333.29] | -2360.2025 [-2807.3820, -1949.0725] |
| Cache hit rate | 0.0% [0.0%, 4.6%] | 40.0% [30.2%, 49.8%] | — |
| Abstain rate | 0.0% [0.0%, 4.6%] | 0.0% [0.0%, 3.7%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 89.9% [85.0%, 94.8%] | 74.0% [66.4%, 81.6%] | — | **langgraph** |
| LLM calls / task | 2.04 [2.00, 2.09] | 0.6900 [0.5700, 0.8200] | -1.4177 [-1.5696, -1.2532] | **chorusgraph** |
| Mean latency | 3335.01 [2881.46, 3848.95] | 1058.54 [815.13, 1333.29] | -2360.2025 [-2807.3820, -1949.0725] | **chorusgraph** |
| Latency p50 | 2429.00 [2311.00, 2558.00] | 1170.50 [27.00, 1246.50] | — | **chorusgraph** |
| Latency p95 | 7659.10 [6174.00, 11196.00] | 3305.95 [1899.70, 4556.05] | — | **chorusgraph** |
| Cost / task | 0.0002 [0.0001, 0.0002] | 0.0001 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 4.6%] | 40.0% [30.2%, 49.8%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 552.35 [509.34, 595.16] | 155.65 [128.49, 183.02] | — | **chorusgraph** |
| Tokens out / task | 116.19 [110.16, 122.56] | 53.24 [44.11, 62.84] | — | **chorusgraph** |
| Tool calls / task | 0.8861 [0.8101, 0.9620] | 0.3000 [0.2100, 0.3900] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 4.6%] | 0.0% [0.0%, 3.7%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 7.32 [6.89, 7.76] | — | **langgraph** |
| Abstain rate | 0.0% [0.0%, 4.6%] | 0.0% [0.0%, 3.7%] | — | **tie** |

Paired tasks: **79** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 2 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 73.7% [66.1%, 81.4%] | 82.0% [75.7%, 88.3%] | — |
| LLM calls / task | 2.97 [2.81, 3.14] | 1.53 [1.38, 1.69] | -1.4343 [-1.6869, -1.1818] |
| Mean latency | 7275.49 [6454.50, 8133.83] | 4175.27 [3816.94, 4540.76] | -3092.5253 [-3941.2669, -2304.0217] |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 63.0% [54.2%, 71.8%] | — |
| Abstain rate | 31.3% [21.6%, 41.0%] | 25.0% [15.7%, 34.3%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 73.7% [66.1%, 81.4%] | 82.0% [75.7%, 88.3%] | — | **chorusgraph** |
| LLM calls / task | 2.97 [2.81, 3.14] | 1.53 [1.38, 1.69] | -1.4343 [-1.6869, -1.1818] | **chorusgraph** |
| Mean latency | 7275.49 [6454.50, 8133.83] | 4175.27 [3816.94, 4540.76] | -3092.5253 [-3941.2669, -2304.0217] | **chorusgraph** |
| Latency p50 | 5974.00 [5257.00, 7703.00] | 3526.00 [3359.00, 3933.00] | — | **chorusgraph** |
| Latency p95 | 15817.00 [11487.56, 17781.20] | 7832.35 [6143.95, 9241.85] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0002 [0.0002, 0.0003] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 63.0% [54.2%, 71.8%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 906.49 [834.61, 986.15] | 971.98 [885.50, 1071.20] | — | **langgraph** |
| Tokens out / task | 317.05 [296.41, 340.32] | 131.29 [109.20, 155.44] | — | **chorusgraph** |
| Tool calls / task | 1.28 [1.17, 1.40] | 0.4100 [0.3000, 0.5200] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 31.3% [21.6%, 41.0%] | 25.0% [15.7%, 34.3%] | — | **langgraph** |

Paired tasks: **99** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 7 metrics, LangGraph wins 5 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 65.0% [56.4%, 73.6%] | 78.0% [71.0%, 85.0%] | — |
| LLM calls / task | 3.83 [3.53, 4.13] | 3.01 [2.69, 3.33] | -0.8200 [-1.0200, -0.6200] |
| Mean latency | 9925.51 [8914.65, 10873.90] | 10290.64 [9113.50, 11538.93] | 365.13 [-371.89, 1093.85] |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 57.0% [47.7%, 66.3%] | — |
| Abstain rate | 15.0% [6.7%, 23.3%] | 4.0% [0.0%, 9.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 65.0% [56.4%, 73.6%] | 78.0% [71.0%, 85.0%] | — | **chorusgraph** |
| LLM calls / task | 3.83 [3.53, 4.13] | 3.01 [2.69, 3.33] | -0.8200 [-1.0200, -0.6200] | **chorusgraph** |
| Mean latency | 9925.51 [8914.65, 10873.90] | 10290.64 [9113.50, 11538.93] | 365.13 [-371.89, 1093.85] | **langgraph** |
| Latency p50 | 10569.00 [8890.00, 12537.50] | 9955.00 [7262.50, 12820.50] | — | **chorusgraph** |
| Latency p95 | 16318.85 [15194.35, 17751.45] | 19465.70 [17712.44, 22006.60] | — | **langgraph** |
| Cost / task | 0.0003 [0.0003, 0.0003] | 0.0003 [0.0002, 0.0003] | -0.0000 [-0.0000, -0.0000] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 57.0% [47.7%, 66.3%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 2.25 [1.93, 2.58] | — | **inconclusive** |
| Tokens in / task | 834.70 [724.72, 941.79] | 949.66 [821.03, 1078.32] | — | **langgraph** |
| Tokens out / task | 294.32 [263.08, 326.68] | 223.43 [197.74, 249.74] | — | **chorusgraph** |
| Tool calls / task | 0.8700 [0.7300, 1.0100] | 0.6100 [0.4800, 0.7400] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 8.06 [7.41, 8.69] | — | **langgraph** |
| Abstain rate | 15.0% [6.7%, 23.3%] | 4.0% [0.0%, 9.8%] | — | **langgraph** |

Paired tasks: **100** (same task/case IDs)
