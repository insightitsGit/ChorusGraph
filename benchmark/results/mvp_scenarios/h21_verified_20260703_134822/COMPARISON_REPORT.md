# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 87.5% [80.5%, 94.5%] | 97.5% [95.4%, 99.6%] | — |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] |
| Mean latency | 4687.77 [4104.77, 5334.15] | 1501.42 [928.27, 2144.83] | -3186.3500 [-3930.9419, -2446.7575] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 87.5% [80.5%, 94.5%] | 97.5% [95.4%, 99.6%] | — | **chorusgraph** |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] | **chorusgraph** |
| Mean latency | 4687.77 [4104.77, 5334.15] | 1501.42 [928.27, 2144.83] | -3186.3500 [-3930.9419, -2446.7575] | **chorusgraph** |
| Latency p50 | 4123.50 [3733.00, 4380.00] | 21.00 [8.50, 2437.00] | — | **chorusgraph** |
| Latency p95 | 8865.50 [6043.15, 11291.00] | 5136.00 [2881.45, 7706.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1139.53 [1005.61, 1279.62] | 332.12 [210.29, 467.72] | — | **chorusgraph** |
| Tokens out / task | 262.38 [231.07, 296.27] | 75.58 [48.02, 106.98] | — | **chorusgraph** |
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
| Task success | 80.0% [70.5%, 89.5%] | 85.0% [77.1%, 92.9%] | — |
| LLM calls / task | 2.02 [2.00, 2.08] | 0.8250 [0.5750, 1.0750] | -1.2000 [-1.4500, -0.9500] |
| Mean latency | 3124.22 [2666.41, 3675.37] | 1639.58 [1036.06, 2305.28] | -1484.6500 [-2198.5825, -743.9906] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 80.0% [70.5%, 89.5%] | 85.0% [77.1%, 92.9%] | — | **chorusgraph** |
| LLM calls / task | 2.02 [2.00, 2.08] | 0.8250 [0.5750, 1.0750] | -1.2000 [-1.4500, -0.9500] | **chorusgraph** |
| Mean latency | 3124.22 [2666.41, 3675.37] | 1639.58 [1036.06, 2305.28] | -1484.6500 [-2198.5825, -743.9906] | **chorusgraph** |
| Latency p50 | 2491.00 [2392.00, 2735.00] | 1369.50 [11.00, 1684.50] | — | **chorusgraph** |
| Latency p95 | 6340.15 [3585.55, 11265.00] | 6692.55 [2774.00, 7415.00] | — | **langgraph** |
| Cost / task | 0.0002 [0.0001, 0.0002] | 0.0001 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 549.27 [495.94, 606.85] | 188.32 [128.67, 254.43] | — | **chorusgraph** |
| Tokens out / task | 119.15 [109.80, 130.85] | 58.00 [40.20, 78.76] | — | **chorusgraph** |
| Tool calls / task | 0.9250 [0.8244, 1.0250] | 0.5250 [0.3500, 0.7000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 3.20 [2.90, 3.50] | — | **langgraph** |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 75.0% [64.2%, 85.8%] | 75.0% [64.2%, 85.8%] | — |
| LLM calls / task | 3.08 [2.80, 3.38] | 1.95 [1.62, 2.30] | -1.1250 [-1.5250, -0.7250] |
| Mean latency | 7257.02 [5944.11, 8777.73] | 5130.45 [4054.38, 6333.08] | -2126.5750 [-3299.3987, -1061.9663] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 45.0% [29.8%, 60.2%] | — |
| Abstain rate | 30.0% [14.6%, 45.4%] | 30.0% [14.6%, 45.4%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 75.0% [64.2%, 85.8%] | 75.0% [64.2%, 85.8%] | — | **tie** |
| LLM calls / task | 3.08 [2.80, 3.38] | 1.95 [1.62, 2.30] | -1.1250 [-1.5250, -0.7250] | **chorusgraph** |
| Mean latency | 7257.02 [5944.11, 8777.73] | 5130.45 [4054.38, 6333.08] | -2126.5750 [-3299.3987, -1061.9663] | **chorusgraph** |
| Latency p50 | 5901.50 [5145.50, 7448.50] | 3557.50 [3111.50, 4915.50] | — | **chorusgraph** |
| Latency p95 | 13408.60 [10802.06, 27224.00] | 12376.80 [7070.15, 18044.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0002 [0.0002, 0.0002] | -0.0001 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 45.0% [29.8%, 60.2%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 982.12 [851.63, 1125.43] | 588.38 [476.15, 710.05] | — | **chorusgraph** |
| Tokens out / task | 325.62 [291.70, 365.48] | 187.70 [141.67, 235.03] | — | **chorusgraph** |
| Tool calls / task | 1.38 [1.18, 1.60] | 0.7000 [0.4750, 0.9250] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 30.0% [14.6%, 45.4%] | 30.0% [14.6%, 45.4%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 2 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 62.5% [49.2%, 75.8%] | 50.0% [35.2%, 64.8%] | — |
| LLM calls / task | 3.88 [3.40, 4.35] | 2.02 [1.73, 2.40] | -1.8500 [-2.4000, -1.3000] |
| Mean latency | 10287.25 [8654.12, 11885.07] | 7308.02 [6052.65, 8653.03] | -2979.2250 [-4536.3925, -1434.3931] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — |
| Abstain rate | 7.5% [0.0%, 19.9%] | 20.0% [5.2%, 34.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 62.5% [49.2%, 75.8%] | 50.0% [35.2%, 64.8%] | — | **langgraph** |
| LLM calls / task | 3.88 [3.40, 4.35] | 2.02 [1.73, 2.40] | -1.8500 [-2.4000, -1.3000] | **chorusgraph** |
| Mean latency | 10287.25 [8654.12, 11885.07] | 7308.02 [6052.65, 8653.03] | -2979.2250 [-4536.3925, -1434.3931] | **chorusgraph** |
| Latency p50 | 12192.00 [7898.00, 13596.00] | 5624.50 [4409.00, 9142.00] | — | **chorusgraph** |
| Latency p95 | 16921.85 [16322.50, 19198.00] | 16564.10 [11473.30, 17750.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0003] | 0.0001 [0.0001, 0.0002] | -0.0002 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.62 [1.42, 1.81] | — | **inconclusive** |
| Tokens in / task | 870.95 [697.54, 1035.42] | 296.65 [224.52, 383.01] | — | **chorusgraph** |
| Tokens out / task | 284.05 [241.39, 326.33] | 150.65 [121.70, 181.90] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.1500 [0.0000, 0.3500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 2.02 [1.73, 2.40] | — | **langgraph** |
| Abstain rate | 7.5% [0.0%, 19.9%] | 20.0% [5.2%, 34.8%] | — | **chorusgraph** |

Paired tasks: **40** (same task/case IDs)
