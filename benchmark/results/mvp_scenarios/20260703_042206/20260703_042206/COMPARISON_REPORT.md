# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| latency_ms_p50 | 3926.50 [3747.00, 4283.00] | 72.00 [32.50, 2486.00] | — | **chorusgraph** |
| latency_ms_p95 | 10321.35 [6993.05, 17942.00] | 4596.80 [2757.20, 6350.00] | — | **chorusgraph** |
| latency_ms_mean | 5194.10 [4334.07, 6168.69] | 1386.30 [885.38, 1922.50] | -3807.8000 [-4611.5350, -3044.1244] | **chorusgraph** |
| cost_usd_per_task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| llm_calls_per_task | 3.33 [2.95, 3.73] | 0.9250 [0.6000, 1.2500] | -2.4000 [-2.8750, -1.9250] | **chorusgraph** |
| tokens_in_per_task | 1123.78 [990.12, 1264.10] | 336.40 [213.62, 470.70] | — | **chorusgraph** |
| tokens_out_per_task | 254.75 [223.70, 287.98] | 74.53 [47.37, 106.11] | — | **chorusgraph** |
| tool_calls_per_task | 0.8250 [0.6750, 0.9750] | 0.3750 [0.2250, 0.5500] | — | **chorusgraph** |
| task_success_rate | 75.0% [64.2%, 85.8%] | 85.0% [77.1%, 92.9%] | — | **chorusgraph** |
| error_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| cache_hit_rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| llm_calls_on_cache_hit_mean | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| embed_count_per_task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| abstain_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Finance Multi (FL2 vs FC2)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 1 metrics)

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| latency_ms_p50 | 2509.00 [2355.00, 2732.00] | 1168.50 [22.50, 1255.00] | — | **chorusgraph** |
| latency_ms_p95 | 6757.10 [3966.85, 12127.00] | 2714.05 [1919.95, 6818.00] | — | **chorusgraph** |
| latency_ms_mean | 3245.47 [2697.37, 3903.31] | 1056.95 [641.25, 1557.42] | -2188.5250 [-2862.1175, -1553.8869] | **chorusgraph** |
| cost_usd_per_task | 0.0002 [0.0001, 0.0002] | 0.0001 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| llm_calls_per_task | 2.02 [2.00, 2.08] | 0.6750 [0.4500, 0.9000] | -1.3500 [-1.5750, -1.1250] | **chorusgraph** |
| tokens_in_per_task | 573.25 [515.85, 633.86] | 152.40 [97.87, 211.71] | — | **chorusgraph** |
| tokens_out_per_task | 121.92 [112.77, 132.65] | 46.48 [30.90, 63.38] | — | **chorusgraph** |
| tool_calls_per_task | 0.9250 [0.8244, 1.0250] | 0.4500 [0.2750, 0.6250] | — | **chorusgraph** |
| task_success_rate | 70.0% [58.1%, 81.9%] | 87.5% [80.5%, 94.5%] | — | **chorusgraph** |
| error_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| cache_hit_rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| llm_calls_on_cache_hit_mean | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| embed_count_per_task | 0.0000 [0.0000, 0.0000] | 3.05 [2.75, 3.35] | — | **langgraph** |
| abstain_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** tie (Chorus wins 4 metrics, LangGraph wins 4 metrics)

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| latency_ms_p50 | 5781.50 [4782.50, 7862.00] | 5686.50 [5007.50, 8007.50] | — | **chorusgraph** |
| latency_ms_p95 | 12221.05 [11029.38, 17363.00] | 11634.20 [10992.05, 13976.00] | — | **chorusgraph** |
| latency_ms_mean | 6797.50 [5707.88, 7947.09] | 6742.32 [5739.67, 7812.14] | -55.1750 [-538.9919, 398.3600] | **chorusgraph** |
| cost_usd_per_task | 0.0003 [0.0003, 0.0004] | 0.0003 [0.0003, 0.0004] | 0.0000 [-0.0000, 0.0000] | **langgraph** |
| llm_calls_per_task | 3.00 [2.75, 3.25] | 3.00 [2.75, 3.27] | 0.0000 [-0.0750, 0.0750] | **tie** |
| tokens_in_per_task | 926.30 [827.21, 1030.27] | 938.42 [832.17, 1053.56] | — | **langgraph** |
| tokens_out_per_task | 314.82 [289.07, 342.84] | 321.75 [294.97, 351.93] | — | **langgraph** |
| tool_calls_per_task | 1.30 [1.15, 1.45] | 1.32 [1.18, 1.48] | — | **langgraph** |
| task_success_rate | 72.5% [61.1%, 83.9%] | 72.5% [61.1%, 83.9%] | — | **tie** |
| error_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| cache_hit_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| llm_calls_on_cache_hit_mean | — | — | — | **inconclusive** |
| embed_count_per_task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| abstain_rate | 30.0% [14.6%, 45.4%] | 32.5% [17.0%, 48.0%] | — | **chorusgraph** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 3 metrics)

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| latency_ms_p50 | 12475.50 [8106.00, 13191.00] | 13.50 [11.00, 3888.00] | — | **chorusgraph** |
| latency_ms_p95 | 16030.95 [14526.60, 16746.00] | 15788.85 [7139.90, 22514.00] | — | **chorusgraph** |
| latency_ms_mean | 10145.27 [8764.21, 11527.67] | 3195.72 [1743.02, 4941.13] | -6949.5500 [-9302.9506, -4589.0206] | **chorusgraph** |
| cost_usd_per_task | 0.0003 [0.0002, 0.0004] | 0.0001 [0.0000, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| llm_calls_per_task | 3.85 [3.38, 4.33] | 1.02 [0.55, 1.57] | -2.8250 [-3.5750, -2.1000] | **chorusgraph** |
| tokens_in_per_task | 789.42 [625.23, 951.98] | 138.25 [60.85, 240.06] | — | **chorusgraph** |
| tokens_out_per_task | 306.93 [257.15, 355.66] | 65.33 [34.82, 103.05] | — | **chorusgraph** |
| tool_calls_per_task | 0.8750 [0.6500, 1.1000] | 0.1500 [0.0000, 0.3500] | — | **chorusgraph** |
| task_success_rate | 57.5% [43.5%, 71.5%] | 45.0% [29.8%, 60.2%] | — | **langgraph** |
| error_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| cache_hit_rate | 0.0% [0.0%, 8.8%] | 62.5% [49.2%, 75.8%] | — | **chorusgraph** |
| llm_calls_on_cache_hit_mean | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| embed_count_per_task | 0.0000 [0.0000, 0.0000] | 1.02 [0.55, 1.57] | — | **langgraph** |
| abstain_rate | 10.0% [0.0%, 23.1%] | 2.5% [0.0%, 12.9%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)
