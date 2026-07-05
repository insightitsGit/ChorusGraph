# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 90.0% [84.0%, 96.0%] | 100.0% [100.0%, 100.0%] | — |
| LLM calls / task | 3.35 [3.00, 3.75] | 0.9250 [0.6000, 1.2500] | -2.4250 [-2.9000, -1.9500] |
| Mean latency | 5051.00 [4322.55, 5888.84] | 1410.42 [881.44, 2013.21] | -3640.5750 [-4288.5169, -3010.1613] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 90.0% [84.0%, 96.0%] | 100.0% [100.0%, 100.0%] | — | **chorusgraph** |
| LLM calls / task | 3.35 [3.00, 3.75] | 0.9250 [0.6000, 1.2500] | -2.4250 [-2.9000, -1.9500] | **chorusgraph** |
| Mean latency | 5051.00 [4322.55, 5888.84] | 1410.42 [881.44, 2013.21] | -3640.5750 [-4288.5169, -3010.1613] | **chorusgraph** |
| Latency p50 | 4037.50 [3669.00, 4521.50] | 104.00 [37.00, 2311.26] | — | **chorusgraph** |
| Latency p95 | 10062.25 [7127.15, 13487.00] | 4850.80 [2589.65, 6960.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1154.55 [1022.72, 1296.39] | 338.20 [215.34, 472.60] | — | **chorusgraph** |
| Tokens out / task | 263.48 [233.85, 296.38] | 76.40 [48.35, 108.80] | — | **chorusgraph** |
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
| Mean latency | 3396.30 [2786.81, 4090.97] | 1573.10 [1016.36, 2198.91] | -1823.2000 [-2662.2706, -1007.2969] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 75.0% [64.2%, 85.8%] | 87.5% [80.5%, 94.5%] | — | **chorusgraph** |
| LLM calls / task | 2.05 [2.00, 2.12] | 0.8250 [0.5750, 1.0750] | -1.2250 [-1.4750, -0.9750] | **chorusgraph** |
| Mean latency | 3396.30 [2786.81, 4090.97] | 1573.10 [1016.36, 2198.91] | -1823.2000 [-2662.2706, -1007.2969] | **chorusgraph** |
| Latency p50 | 2548.00 [2439.00, 2712.00] | 1300.00 [39.50, 1515.00] | — | **chorusgraph** |
| Latency p95 | 9285.05 [3589.89, 10971.00] | 6917.35 [3154.95, 7878.00] | — | **chorusgraph** |
| Cost / task | 0.0002 [0.0001, 0.0002] | 0.0001 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 40.0% [24.6%, 55.4%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 565.25 [511.92, 620.30] | 263.23 [163.73, 384.96] | — | **chorusgraph** |
| Tokens out / task | 121.72 [113.20, 131.70] | 56.12 [39.97, 72.90] | — | **chorusgraph** |
| Tool calls / task | 0.9250 [0.8244, 1.0250] | 0.5250 [0.3500, 0.7000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 8.40 [7.80, 9.00] | — | **langgraph** |
| Abstain rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 1 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 75.0% [64.2%, 85.8%] | 0.0% [0.0%, 49.0%] | — |
| LLM calls / task | 3.05 [2.77, 3.35] | 2.00 [2.00, 2.00] | 0.0000 [0.0000, 0.0000] |
| Mean latency | 7781.60 [6319.43, 9468.48] | 3216.75 [3184.00, 3256.25] | 55.50 [-80.00, 210.00] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 49.0%] | — |
| Abstain rate | 30.0% [14.6%, 45.4%] | 100.0% [100.0%, 100.0%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 75.0% [64.2%, 85.8%] | 0.0% [0.0%, 49.0%] | — | **langgraph** |
| LLM calls / task | 3.05 [2.77, 3.35] | 2.00 [2.00, 2.00] | 0.0000 [0.0000, 0.0000] | **chorusgraph** |
| Mean latency | 7781.60 [6319.43, 9468.48] | 3216.75 [3184.00, 3256.25] | 55.50 [-80.00, 210.00] | **chorusgraph** |
| Latency p50 | 5972.50 [5222.00, 8257.00] | 3208.00 [3174.00, 3277.00] | — | **chorusgraph** |
| Latency p95 | 17561.50 [12060.00, 24523.00] | 3268.75 [3194.00, 3277.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0002 [0.0002, 0.0002] | -0.0000 [-0.0000, 0.0000] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 49.0%] | — | **tie** |
| LLM calls on cache hit | — | — | — | **inconclusive** |
| Tokens in / task | 954.42 [838.53, 1085.86] | 501.25 [493.75, 505.00] | — | **chorusgraph** |
| Tokens out / task | 330.30 [295.82, 369.01] | 243.50 [227.00, 260.00] | — | **chorusgraph** |
| Tool calls / task | 1.35 [1.18, 1.57] | 1.00 [1.00, 1.00] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 49.0%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 30.0% [14.6%, 45.4%] | 100.0% [100.0%, 100.0%] | — | **chorusgraph** |

Paired tasks: **4** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 2 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 62.5% [49.2%, 75.8%] | 85.7% [75.4%, 96.0%] | — |
| LLM calls / task | 3.80 [3.35, 4.25] | 1.93 [1.79, 2.00] | -0.0714 [-0.2143, 0.0000] |
| Mean latency | 10304.30 [8756.78, 11845.55] | 5932.43 [5044.59, 6907.68] | 1635.71 [861.43, 2436.77] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 7.1% [0.0%, 31.5%] | — |
| Abstain rate | 15.0% [0.9%, 29.1%] | 0.0% [0.0%, 21.5%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 62.5% [49.2%, 75.8%] | 85.7% [75.4%, 96.0%] | — | **chorusgraph** |
| LLM calls / task | 3.80 [3.35, 4.25] | 1.93 [1.79, 2.00] | -0.0714 [-0.2143, 0.0000] | **chorusgraph** |
| Mean latency | 10304.30 [8756.78, 11845.55] | 5932.43 [5044.59, 6907.68] | 1635.71 [861.43, 2436.77] | **chorusgraph** |
| Latency p50 | 11208.50 [8763.50, 13341.00] | 5493.00 [4804.00, 6218.00] | — | **chorusgraph** |
| Latency p95 | 17063.05 [15582.10, 18285.00] | 9423.00 [6218.00, 10333.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | 0.0000 [0.0000, 0.0000] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 7.1% [0.0%, 31.5%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 883.58 [705.49, 1056.53] | 156.57 [149.79, 163.64] | — | **chorusgraph** |
| Tokens out / task | 316.50 [263.95, 370.58] | 146.29 [131.78, 159.64] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.0000 [0.0000, 0.0000] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 21.5%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 5.86 [5.57, 6.00] | — | **langgraph** |
| Abstain rate | 15.0% [0.9%, 29.1%] | 0.0% [0.0%, 21.5%] | — | **langgraph** |

Paired tasks: **14** (same task/case IDs)
