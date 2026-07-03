# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 90.0% [84.0%, 96.0%] | 97.5% [95.4%, 99.6%] | — |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] |
| Mean latency | 4512.60 [3933.95, 5120.61] | 1517.28 [938.22, 2176.98] | -2995.3250 [-3557.8063, -2417.8631] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 90.0% [84.0%, 96.0%] | 97.5% [95.4%, 99.6%] | — | **chorusgraph** |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] | **chorusgraph** |
| Mean latency | 4512.60 [3933.95, 5120.61] | 1517.28 [938.22, 2176.98] | -2995.3250 [-3557.8063, -2417.8631] | **chorusgraph** |
| Latency p50 | 3667.00 [3609.00, 4056.00] | 39.00 [9.00, 2327.19] | — | **chorusgraph** |
| Latency p95 | 9023.95 [6976.45, 9738.00] | 5413.30 [3001.85, 7790.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1147.42 [1016.54, 1286.72] | 332.88 [210.12, 468.41] | — | **chorusgraph** |
| Tokens out / task | 260.25 [227.90, 295.53] | 75.30 [47.82, 107.28] | — | **chorusgraph** |
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
| LLM calls / task | 2.08 [2.00, 2.15] | 0.8250 [0.5750, 1.0750] | -1.2500 [-1.5000, -1.0000] |
| Mean latency | 3245.07 [2678.85, 3882.46] | 1494.95 [1022.77, 2026.93] | -1750.1250 [-2383.4844, -1095.1331] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 75.0% [64.2%, 85.8%] | 85.0% [77.1%, 92.9%] | — | **chorusgraph** |
| LLM calls / task | 2.08 [2.00, 2.15] | 0.8250 [0.5750, 1.0750] | -1.2500 [-1.5000, -1.0000] | **chorusgraph** |
| Mean latency | 3245.07 [2678.85, 3882.46] | 1494.95 [1022.77, 2026.93] | -1750.1250 [-2383.4844, -1095.1331] | **chorusgraph** |
| Latency p50 | 2423.50 [2221.50, 2721.50] | 1309.00 [11.50, 1873.50] | — | **chorusgraph** |
| Latency p95 | 7125.40 [4658.40, 11783.00] | 4477.40 [2830.65, 6440.00] | — | **chorusgraph** |
| Cost / task | 0.0002 [0.0001, 0.0002] | 0.0001 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 556.12 [503.00, 611.10] | 242.12 [156.14, 347.55] | — | **chorusgraph** |
| Tokens out / task | 119.88 [109.67, 131.40] | 54.65 [39.38, 70.58] | — | **chorusgraph** |
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
| Task success | 70.0% [58.1%, 81.9%] | 72.5% [61.1%, 83.9%] | — |
| LLM calls / task | 2.98 [2.73, 3.23] | 1.95 [1.62, 2.30] | -1.0250 [-1.4500, -0.6500] |
| Mean latency | 6503.85 [5366.48, 7749.21] | 4511.25 [3622.04, 5462.85] | -1992.6000 [-3136.1331, -1043.2138] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 45.0% [29.8%, 60.2%] | — |
| Abstain rate | 32.5% [17.0%, 48.0%] | 30.0% [14.6%, 45.4%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 70.0% [58.1%, 81.9%] | 72.5% [61.1%, 83.9%] | — | **chorusgraph** |
| LLM calls / task | 2.98 [2.73, 3.23] | 1.95 [1.62, 2.30] | -1.0250 [-1.4500, -0.6500] | **chorusgraph** |
| Mean latency | 6503.85 [5366.48, 7749.21] | 4511.25 [3622.04, 5462.85] | -1992.6000 [-3136.1331, -1043.2138] | **chorusgraph** |
| Latency p50 | 5205.50 [4182.50, 6720.00] | 3137.00 [2828.88, 4643.50] | — | **chorusgraph** |
| Latency p95 | 14846.90 [10557.00, 16373.00] | 11083.95 [7065.00, 13950.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0002 [0.0002, 0.0002] | -0.0001 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 45.0% [29.8%, 60.2%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 912.33 [814.53, 1016.50] | 587.70 [475.46, 709.38] | — | **chorusgraph** |
| Tokens out / task | 321.05 [292.74, 353.05] | 187.10 [142.35, 232.35] | — | **chorusgraph** |
| Tool calls / task | 1.30 [1.15, 1.45] | 0.7000 [0.4750, 0.9250] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 32.5% [17.0%, 48.0%] | 30.0% [14.6%, 45.4%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 3 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 70.0% [58.1%, 81.9%] | 52.5% [37.9%, 67.1%] | — |
| LLM calls / task | 3.83 [3.38, 4.28] | 2.02 [1.73, 2.40] | -1.8000 [-2.3500, -1.2750] |
| Mean latency | 9261.15 [7790.97, 10694.95] | 6859.98 [5590.40, 8283.43] | -2401.1750 [-3937.0050, -915.9738] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — |
| Abstain rate | 12.5% [0.0%, 26.1%] | 20.0% [5.2%, 34.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 70.0% [58.1%, 81.9%] | 52.5% [37.9%, 67.1%] | — | **langgraph** |
| LLM calls / task | 3.83 [3.38, 4.28] | 2.02 [1.73, 2.40] | -1.8000 [-2.3500, -1.2750] | **chorusgraph** |
| Mean latency | 9261.15 [7790.97, 10694.95] | 6859.98 [5590.40, 8283.43] | -2401.1750 [-3937.0050, -915.9738] | **chorusgraph** |
| Latency p50 | 10175.00 [7554.23, 12085.50] | 5117.50 [4132.00, 7105.00] | — | **chorusgraph** |
| Latency p95 | 15027.70 [14376.50, 17614.00] | 17513.55 [10917.55, 19383.00] | — | **langgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0002] | -0.0002 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 65.0% [52.1%, 77.9%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.62 [1.42, 1.81] | — | **inconclusive** |
| Tokens in / task | 859.05 [692.05, 1021.13] | 297.12 [225.88, 388.68] | — | **chorusgraph** |
| Tokens out / task | 298.88 [253.75, 343.45] | 156.10 [130.87, 184.55] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.1500 [0.0000, 0.3500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 6.25 [5.65, 7.00] | — | **langgraph** |
| Abstain rate | 12.5% [0.0%, 26.1%] | 20.0% [5.2%, 34.8%] | — | **chorusgraph** |

Paired tasks: **40** (same task/case IDs)
