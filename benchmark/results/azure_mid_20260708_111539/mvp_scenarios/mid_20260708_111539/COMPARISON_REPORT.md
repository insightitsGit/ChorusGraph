# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal). Embeds / task is inconclusive when only one side has an embed path; tokens in / task is inconclusive when CIs overlap.
For **abstain rate**, **latency**, **LLM calls**, and **cost**, lower is better.

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 11 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 87.0% [81.8%, 92.2%] | 98.0% [96.6%, 99.4%] | — |
| LLM calls / task | 3.24 [3.01, 3.49] | 0.7700 [0.5800, 0.9700] | -2.4700 [-2.7600, -2.2000] |
| Mean latency | 4759.78 [4332.38, 5243.08] | 1347.88 [970.07, 1753.35] | -3411.9000 [-3902.8233, -2938.8807] |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 52.0% [42.5%, 61.5%] | — |
| Abstain rate | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 87.0% [81.8%, 92.2%] | 98.0% [96.6%, 99.4%] | — | **chorusgraph** |
| LLM calls / task | 3.24 [3.01, 3.49] | 0.7700 [0.5800, 0.9700] | -2.4700 [-2.7600, -2.2000] | **chorusgraph** |
| Mean latency | 4759.78 [4332.38, 5243.08] | 1347.88 [970.07, 1753.35] | -3411.9000 [-3902.8233, -2938.8807] | **chorusgraph** |
| Latency p50 | 3801.00 [3673.00, 4275.00] | 31.00 [24.00, 258.00] | — | **chorusgraph** |
| Latency p95 | 9024.60 [7845.05, 12802.15] | 6279.55 [3148.98, 6943.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0003] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 52.0% [42.5%, 61.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1116.28 [1034.69, 1199.29] | 270.63 [199.07, 342.59] | — | **chorusgraph** |
| Tokens out / task | 251.53 [232.08, 272.61] | 59.05 [43.31, 75.12] | — | **chorusgraph** |
| Tool calls / task | 0.8200 [0.7400, 0.9000] | 0.3200 [0.2300, 0.4200] | — | **chorusgraph** |
| Error rate | 1.0% [0.0%, 5.4%] | 0.0% [0.0%, 3.7%] | — | **chorusgraph** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] | — | **tie** |

Paired tasks: **100** (same task/case IDs)

## Finance Multi (FL2 vs FC2)

**Overall:** chorusgraph (Chorus wins 11 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 87.0% [81.8%, 92.2%] | 94.0% [90.8%, 97.2%] | — |
| LLM calls / task | 2.03 [1.99, 2.07] | 0.6900 [0.5700, 0.8200] | -1.3400 [-1.4700, -1.2100] |
| Mean latency | 3268.76 [2898.29, 3689.29] | 1084.69 [839.06, 1364.47] | -2184.0700 [-2565.0278, -1823.7145] |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 40.0% [30.2%, 49.8%] | — |
| Abstain rate | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 87.0% [81.8%, 92.2%] | 94.0% [90.8%, 97.2%] | — | **chorusgraph** |
| LLM calls / task | 2.03 [1.99, 2.07] | 0.6900 [0.5700, 0.8200] | -1.3400 [-1.4700, -1.2100] | **chorusgraph** |
| Mean latency | 3268.76 [2898.29, 3689.29] | 1084.69 [839.06, 1364.47] | -2184.0700 [-2565.0278, -1823.7145] | **chorusgraph** |
| Latency p50 | 2581.00 [2474.00, 2700.50] | 1154.50 [26.00, 1272.50] | — | **chorusgraph** |
| Latency p95 | 8834.00 [4208.24, 11025.00] | 3444.90 [2035.20, 5437.05] | — | **chorusgraph** |
| Cost / task | 0.0002 [0.0002, 0.0002] | 0.0001 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 40.0% [30.2%, 49.8%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 583.13 [542.20, 622.10] | 156.87 [129.41, 184.60] | — | **chorusgraph** |
| Tokens out / task | 119.40 [113.60, 125.53] | 52.49 [43.34, 61.92] | — | **chorusgraph** |
| Tool calls / task | 0.9000 [0.8300, 0.9600] | 0.5000 [0.4000, 0.6100] | — | **chorusgraph** |
| Error rate | 1.0% [0.0%, 5.4%] | 0.0% [0.0%, 3.7%] | — | **chorusgraph** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 8.32 [7.92, 8.72] | — | **inconclusive** |
| Abstain rate | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] | — | **tie** |

Paired tasks: **100** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 74.0% [66.4%, 81.6%] | 79.0% [72.2%, 85.8%] | — |
| LLM calls / task | 3.00 [2.83, 3.17] | 1.56 [1.42, 1.72] | -1.4400 [-1.6900, -1.1800] |
| Mean latency | 7035.84 [6236.53, 7862.07] | 3990.29 [3552.97, 4552.93] | -3045.5500 [-3796.3382, -2363.3515] |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 60.0% [50.9%, 69.1%] | — |
| Abstain rate | 30.0% [20.4%, 39.6%] | 28.0% [18.5%, 37.5%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 74.0% [66.4%, 81.6%] | 79.0% [72.2%, 85.8%] | — | **chorusgraph** |
| LLM calls / task | 3.00 [2.83, 3.17] | 1.56 [1.42, 1.72] | -1.4400 [-1.6900, -1.1800] | **chorusgraph** |
| Mean latency | 7035.84 [6236.53, 7862.07] | 3990.29 [3552.97, 4552.93] | -3045.5500 [-3796.3382, -2363.3515] | **chorusgraph** |
| Latency p50 | 5996.50 [5348.50, 7152.00] | 3350.50 [3195.50, 3587.50] | — | **chorusgraph** |
| Latency p95 | 14544.05 [11132.45, 21330.95] | 7564.30 [5632.70, 9192.80] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0002 [0.0002, 0.0003] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 60.0% [50.9%, 69.1%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 925.90 [850.67, 1004.14] | 963.33 [875.22, 1063.03] | — | **inconclusive** |
| Tokens out / task | 320.25 [298.04, 343.74] | 137.87 [115.83, 161.16] | — | **chorusgraph** |
| Tool calls / task | 1.30 [1.18, 1.42] | 0.4400 [0.3400, 0.5500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 30.0% [20.4%, 39.6%] | 28.0% [18.5%, 37.5%] | — | **chorusgraph** |

Paired tasks: **100** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 7 metrics, LangGraph wins 3 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 59.0% [49.9%, 68.1%] | 85.0% [79.3%, 90.7%] | — |
| LLM calls / task | 3.82 [3.53, 4.11] | 3.15 [2.82, 3.48] | -0.6700 [-0.8600, -0.4898] |
| Mean latency | 10296.27 [9254.11, 11268.16] | 10752.54 [9540.81, 11959.34] | 456.27 [-355.61, 1336.77] |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 51.0% [41.4%, 60.6%] | — |
| Abstain rate | 16.0% [7.6%, 24.4%] | 2.0% [0.0%, 7.0%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 59.0% [49.9%, 68.1%] | 85.0% [79.3%, 90.7%] | — | **chorusgraph** |
| LLM calls / task | 3.82 [3.53, 4.11] | 3.15 [2.82, 3.48] | -0.6700 [-0.8600, -0.4898] | **chorusgraph** |
| Mean latency | 10296.27 [9254.11, 11268.16] | 10752.54 [9540.81, 11959.34] | 456.27 [-355.61, 1336.77] | **langgraph** |
| Latency p50 | 10709.00 [9637.50, 11528.00] | 10913.00 [7540.50, 13215.00] | — | **langgraph** |
| Latency p95 | 17478.15 [16562.65, 18369.75] | 19022.20 [18056.75, 21513.30] | — | **langgraph** |
| Cost / task | 0.0003 [0.0003, 0.0003] | 0.0003 [0.0002, 0.0003] | -0.0000 [-0.0000, 0.0000] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 3.7%] | 51.0% [41.4%, 60.6%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 2.22 [1.88, 2.57] | — | **inconclusive** |
| Tokens in / task | 825.23 [721.08, 927.66] | 986.04 [850.47, 1110.12] | — | **inconclusive** |
| Tokens out / task | 290.24 [262.45, 317.02] | 227.82 [201.79, 256.19] | — | **chorusgraph** |
| Tool calls / task | 0.8700 [0.7300, 1.0100] | 0.6700 [0.5200, 0.8000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 8.32 [7.64, 8.97] | — | **inconclusive** |
| Abstain rate | 16.0% [7.6%, 24.4%] | 2.0% [0.0%, 7.0%] | — | **chorusgraph** |

Paired tasks: **100** (same task/case IDs)
