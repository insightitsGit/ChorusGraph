# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| latency_ms_p50 | 3982.00 [3605.00, 4870.50] | 43.50 [23.00, 2391.50] | — | **chorusgraph** |
| latency_ms_p95 | 9683.55 [7614.85, 13166.00] | 4700.05 [2656.25, 6539.00] | — | **chorusgraph** |
| latency_ms_mean | 5030.73 [4305.37, 5850.07] | 1396.47 [882.01, 1963.10] | -3634.2500 [-4420.5144, -2947.7825] | **chorusgraph** |
| cost_usd_per_task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| llm_calls_per_task | 3.35 [2.98, 3.75] | 0.9250 [0.6000, 1.2500] | -2.4250 [-2.9000, -1.9500] | **chorusgraph** |
| tokens_in_per_task | 1124.80 [991.59, 1265.89] | 336.05 [213.27, 470.05] | — | **chorusgraph** |
| tokens_out_per_task | 251.62 [221.95, 283.70] | 76.10 [48.47, 109.61] | — | **chorusgraph** |
| tool_calls_per_task | 0.8250 [0.6750, 0.9750] | 0.3750 [0.2250, 0.5500] | — | **chorusgraph** |
| task_success_rate | 72.5% [61.1%, 83.9%] | 85.0% [77.1%, 92.9%] | — | **chorusgraph** |
| error_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| cache_hit_rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| llm_calls_on_cache_hit_mean | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| embed_count_per_task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| abstain_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Finance Multi (FL2 vs FC2)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 2 metrics)

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| latency_ms_p50 | 2438.00 [2342.50, 2603.00] | 1047.50 [21.50, 1296.00] | — | **chorusgraph** |
| latency_ms_p95 | 6523.50 [4676.15, 10537.00] | 6581.15 [1842.05, 6884.00] | — | **langgraph** |
| latency_ms_mean | 3150.28 [2643.73, 3728.56] | 1301.25 [733.45, 1926.11] | -1849.0250 [-2424.9406, -1229.6631] | **chorusgraph** |
| cost_usd_per_task | 0.0002 [0.0001, 0.0002] | 0.0000 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| llm_calls_per_task | 2.05 [2.00, 2.12] | 0.6750 [0.4500, 0.9000] | -1.3750 [-1.6000, -1.1500] | **chorusgraph** |
| tokens_in_per_task | 555.92 [503.45, 610.33] | 153.55 [98.20, 213.55] | — | **chorusgraph** |
| tokens_out_per_task | 120.25 [112.02, 131.08] | 43.85 [29.52, 59.05] | — | **chorusgraph** |
| tool_calls_per_task | 0.9250 [0.8244, 1.0250] | 0.4500 [0.2750, 0.6250] | — | **chorusgraph** |
| task_success_rate | 70.0% [58.1%, 81.9%] | 87.5% [80.5%, 94.5%] | — | **chorusgraph** |
| error_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| cache_hit_rate | 0.0% [0.0%, 8.8%] | 47.5% [32.5%, 62.5%] | — | **chorusgraph** |
| llm_calls_on_cache_hit_mean | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| embed_count_per_task | 0.0000 [0.0000, 0.0000] | 3.05 [2.75, 3.35] | — | **langgraph** |
| abstain_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** langgraph (Chorus wins 1 metrics, LangGraph wins 9 metrics)

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| latency_ms_p50 | 5320.00 [4672.00, 7549.50] | 9588.50 [9078.00, 9878.50] | — | **langgraph** |
| latency_ms_p95 | 11695.95 [10429.00, 24061.00] | 12638.20 [11019.45, 25485.00] | — | **langgraph** |
| latency_ms_mean | 6779.40 [5533.62, 8296.35] | 9998.27 [9323.04, 10990.76] | 3218.88 [1628.26, 4623.55] | **langgraph** |
| cost_usd_per_task | 0.0003 [0.0003, 0.0004] | 0.0007 [0.0007, 0.0007] | 0.0003 [0.0003, 0.0004] | **langgraph** |
| llm_calls_per_task | 3.02 [2.75, 3.33] | 6.00 [6.00, 6.00] | 2.98 [2.67, 3.25] | **langgraph** |
| tokens_in_per_task | 946.98 [834.57, 1078.66] | 1295.55 [1279.95, 1312.05] | — | **langgraph** |
| tokens_out_per_task | 325.23 [292.70, 364.41] | 819.52 [795.20, 845.00] | — | **langgraph** |
| tool_calls_per_task | 1.32 [1.15, 1.55] | 0.0000 [0.0000, 0.0000] | — | **chorusgraph** |
| task_success_rate | 72.5% [61.1%, 83.9%] | 0.0% [0.0%, 8.8%] | — | **langgraph** |
| error_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| cache_hit_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| llm_calls_on_cache_hit_mean | — | — | — | **inconclusive** |
| embed_count_per_task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| abstain_rate | 30.0% [14.6%, 45.4%] | 0.0% [0.0%, 8.8%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 2 metrics)

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| latency_ms_p50 | 10482.00 [8797.00, 12970.00] | 13.50 [11.00, 2852.00] | — | **chorusgraph** |
| latency_ms_p95 | 16952.10 [15452.20, 17701.00] | 16404.00 [7697.35, 19962.00] | — | **chorusgraph** |
| latency_ms_mean | 10364.30 [8990.45, 11765.20] | 3221.15 [1732.13, 5029.36] | -7143.1500 [-9335.8994, -4962.2725] | **chorusgraph** |
| cost_usd_per_task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0000, 0.0001] | -0.0002 [-0.0003, -0.0002] | **chorusgraph** |
| llm_calls_per_task | 3.88 [3.40, 4.35] | 1.02 [0.55, 1.57] | -2.8500 [-3.5750, -2.1250] | **chorusgraph** |
| tokens_in_per_task | 804.75 [630.57, 971.30] | 140.35 [60.70, 245.86] | — | **chorusgraph** |
| tokens_out_per_task | 312.88 [264.35, 360.05] | 67.53 [37.19, 105.23] | — | **chorusgraph** |
| tool_calls_per_task | 0.8750 [0.6500, 1.1000] | 0.1500 [0.0000, 0.3500] | — | **chorusgraph** |
| task_success_rate | 60.0% [46.3%, 73.7%] | 60.0% [46.3%, 73.7%] | — | **tie** |
| error_rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| cache_hit_rate | 0.0% [0.0%, 8.8%] | 62.5% [49.2%, 75.8%] | — | **chorusgraph** |
| llm_calls_on_cache_hit_mean | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| embed_count_per_task | 0.0000 [0.0000, 0.0000] | 1.02 [0.55, 1.57] | — | **langgraph** |
| abstain_rate | 7.5% [0.0%, 19.9%] | 2.5% [0.0%, 12.9%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)
