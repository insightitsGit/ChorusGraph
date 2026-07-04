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
| Mean latency | 5171.18 [4511.31, 5879.23] | 1605.15 [997.22, 2279.02] | -3566.0250 [-4205.3981, -2927.5494] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 90.0% [84.0%, 96.0%] | 97.5% [95.4%, 99.6%] | — | **chorusgraph** |
| LLM calls / task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] | **chorusgraph** |
| Mean latency | 5171.18 [4511.31, 5879.23] | 1605.15 [997.22, 2279.02] | -3566.0250 [-4205.3981, -2927.5494] | **chorusgraph** |
| Latency p50 | 4093.00 [3830.91, 4474.00] | 15.50 [7.00, 2544.00] | — | **chorusgraph** |
| Latency p95 | 9842.50 [8174.00, 11171.00] | 5559.30 [3092.70, 7294.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1132.15 [998.67, 1271.65] | 333.05 [210.60, 468.78] | — | **chorusgraph** |
| Tokens out / task | 254.35 [224.50, 286.83] | 74.97 [47.95, 106.23] | — | **chorusgraph** |
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
| Task success | 77.5% [67.3%, 87.7%] | 85.0% [77.1%, 92.9%] | — |
| LLM calls / task | 2.08 [2.00, 2.17] | 0.8250 [0.5750, 1.0750] | -1.2500 [-1.5000, -1.0000] |
| Mean latency | 3464.60 [2982.56, 4052.26] | 1478.62 [984.30, 2052.18] | -1985.9750 [-2641.6269, -1323.2956] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 77.5% [67.3%, 87.7%] | 85.0% [77.1%, 92.9%] | — | **chorusgraph** |
| LLM calls / task | 2.08 [2.00, 2.17] | 0.8250 [0.5750, 1.0750] | -1.2500 [-1.5000, -1.0000] | **chorusgraph** |
| Mean latency | 3464.60 [2982.56, 4052.26] | 1478.62 [984.30, 2052.18] | -1985.9750 [-2641.6269, -1323.2956] | **chorusgraph** |
| Latency p50 | 2766.00 [2622.50, 2966.50] | 1388.50 [10.00, 1778.00] | — | **chorusgraph** |
| Latency p95 | 6919.00 [4331.95, 9266.00] | 4381.35 [2780.00, 6835.00] | — | **chorusgraph** |
| Cost / task | 0.0002 [0.0002, 0.0002] | 0.0001 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 584.25 [526.01, 643.63] | 245.57 [157.30, 354.33] | — | **chorusgraph** |
| Tokens out / task | 126.12 [116.97, 137.28] | 56.50 [40.08, 73.78] | — | **chorusgraph** |
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
| Task success | 75.0% [64.2%, 85.8%] | 80.0% [70.5%, 89.5%] | — |
| LLM calls / task | 3.08 [2.80, 3.38] | 1.90 [1.57, 2.27] | -1.1750 [-1.5756, -0.8000] |
| Mean latency | 6928.32 [5706.34, 8253.80] | 4460.10 [3658.80, 5402.80] | -2468.2250 [-3551.6262, -1492.6019] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 50.0% [35.2%, 64.8%] | — |
| Abstain rate | 30.0% [14.6%, 45.4%] | 25.0% [9.8%, 40.2%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 75.0% [64.2%, 85.8%] | 80.0% [70.5%, 89.5%] | — | **chorusgraph** |
| LLM calls / task | 3.08 [2.80, 3.38] | 1.90 [1.57, 2.27] | -1.1750 [-1.5756, -0.8000] | **chorusgraph** |
| Mean latency | 6928.32 [5706.34, 8253.80] | 4460.10 [3658.80, 5402.80] | -2468.2250 [-3551.6262, -1492.6019] | **chorusgraph** |
| Latency p50 | 5522.50 [4639.00, 8124.50] | 3113.00 [2912.50, 4394.50] | — | **chorusgraph** |
| Latency p95 | 12231.70 [10689.00, 20932.00] | 9345.05 [6696.45, 15154.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0003 [0.0002, 0.0004] | -0.0000 [-0.0001, 0.0000] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 50.0% [35.2%, 64.8%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 972.62 [853.19, 1101.56] | 1271.75 [1035.24, 1559.13] | — | **langgraph** |
| Tokens out / task | 333.93 [297.87, 374.00] | 184.07 [134.45, 237.55] | — | **chorusgraph** |
| Tool calls / task | 1.38 [1.20, 1.60] | 0.6500 [0.4250, 0.9000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 30.0% [14.6%, 45.4%] | 25.0% [9.8%, 40.2%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** inconclusive (Chorus wins 0 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|

Paired tasks: **0** (same task/case IDs)
