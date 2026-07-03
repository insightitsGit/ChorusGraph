# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 0 metrics)

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| latency_ms_p50 | 3875.50 [3454.00, 7288.00] | 94.50 [15.50, 2558.00] | — | **chorusgraph** |
| latency_ms_p95 | 8988.40 [5761.60, 9391.00] | 4331.40 [2352.65, 6373.00] | — | **chorusgraph** |
| latency_ms_mean | 5134.67 [3944.18, 6515.70] | 1381.67 [437.66, 2564.97] | -3753.0000 [-5124.1646, -2688.1417] | **chorusgraph** |
| cost_usd_per_task | 0.0004 [0.0003, 0.0005] | 0.0001 [0.0000, 0.0001] | -0.0003 [-0.0004, -0.0002] | **chorusgraph** |
| llm_calls_per_task | 4.00 [3.00, 5.00] | 0.8333 [0.3333, 1.5000] | -3.1667 [-4.1667, -2.1667] | **chorusgraph** |
| tokens_in_per_task | 1358.00 [1073.10, 1681.93] | 295.83 [106.00, 520.34] | — | **chorusgraph** |
| tokens_out_per_task | 290.25 [230.58, 362.42] | 62.67 [21.83, 111.50] | — | **chorusgraph** |
| tool_calls_per_task | 0.7500 [0.5000, 1.0000] | 0.4167 [0.1667, 0.6667] | — | **chorusgraph** |
| task_success_rate | 58.3% [36.0%, 80.7%] | 66.7% [47.1%, 86.2%] | — | **chorusgraph** |
| error_rate | 0.0% [0.0%, 24.2%] | 0.0% [0.0%, 24.2%] | — | **tie** |
| cache_hit_rate | 0.0% [0.0%, 24.2%] | 41.7% [15.3%, 68.0%] | — | **chorusgraph** |
| llm_calls_on_cache_hit_mean | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| embed_count_per_task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| abstain_rate | 0.0% [0.0%, 24.2%] | 0.0% [0.0%, 24.2%] | — | **tie** |

Paired tasks: **12** (same task/case IDs)

## Finance Multi (FL2 vs FC2)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 1 metrics)

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| latency_ms_p50 | 2619.50 [2306.50, 4480.00] | 1206.50 [15.00, 1419.50] | — | **chorusgraph** |
| latency_ms_p95 | 10282.75 [2945.00, 10511.00] | 4041.80 [1369.20, 7036.00] | — | **chorusgraph** |
| latency_ms_mean | 4073.42 [2529.06, 5982.10] | 1270.83 [461.82, 2354.64] | -2802.5833 [-4808.9354, -1099.9021] | **chorusgraph** |
| cost_usd_per_task | 0.0002 [0.0001, 0.0002] | 0.0000 [0.0000, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| llm_calls_per_task | 2.17 [2.00, 2.42] | 0.6667 [0.3333, 1.0000] | -1.5000 [-1.8333, -1.1667] | **chorusgraph** |
| tokens_in_per_task | 573.08 [491.42, 657.17] | 139.50 [66.08, 217.42] | — | **chorusgraph** |
| tokens_out_per_task | 126.83 [112.25, 143.08] | 45.42 [22.33, 71.25] | — | **chorusgraph** |
| tool_calls_per_task | 1.00 [1.00, 1.00] | 0.5833 [0.3333, 0.8333] | — | **chorusgraph** |
| task_success_rate | 50.0% [25.4%, 74.6%] | 66.7% [47.1%, 86.2%] | — | **chorusgraph** |
| error_rate | 0.0% [0.0%, 24.2%] | 0.0% [0.0%, 24.2%] | — | **tie** |
| cache_hit_rate | 0.0% [0.0%, 24.2%] | 41.7% [15.3%, 68.0%] | — | **chorusgraph** |
| llm_calls_on_cache_hit_mean | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| embed_count_per_task | 0.0000 [0.0000, 0.0000] | 3.17 [2.67, 3.67] | — | **langgraph** |
| abstain_rate | 0.0% [0.0%, 24.2%] | 0.0% [0.0%, 24.2%] | — | **tie** |

Paired tasks: **12** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** langgraph (Chorus wins 3 metrics, LangGraph wins 7 metrics)

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| latency_ms_p50 | 5518.50 [4044.50, 11431.50] | 9100.50 [8483.00, 9393.50] | — | **langgraph** |
| latency_ms_p95 | 13771.65 [11178.15, 16388.00] | 10110.90 [9248.00, 10585.00] | — | **chorusgraph** |
| latency_ms_mean | 7713.67 [5398.19, 10171.63] | 9078.17 [8753.84, 9469.33] | 1364.50 [-946.46, 3600.21] | **langgraph** |
| cost_usd_per_task | 0.0004 [0.0003, 0.0004] | 0.0007 [0.0006, 0.0007] | 0.0003 [0.0002, 0.0004] | **langgraph** |
| llm_calls_per_task | 3.17 [2.67, 3.58] | 6.00 [6.00, 6.00] | 2.83 [2.42, 3.25] | **langgraph** |
| tokens_in_per_task | 1046.42 [860.83, 1224.18] | 1284.00 [1251.50, 1315.50] | — | **langgraph** |
| tokens_out_per_task | 340.00 [286.83, 394.26] | 783.50 [744.41, 823.67] | — | **langgraph** |
| tool_calls_per_task | 1.50 [1.25, 1.75] | 0.0000 [0.0000, 0.0000] | — | **chorusgraph** |
| task_success_rate | 83.3% [71.4%, 95.3%] | 33.3% [5.7%, 60.9%] | — | **langgraph** |
| error_rate | 0.0% [0.0%, 24.2%] | 0.0% [0.0%, 24.2%] | — | **tie** |
| cache_hit_rate | 0.0% [0.0%, 24.2%] | 0.0% [0.0%, 24.2%] | — | **tie** |
| llm_calls_on_cache_hit_mean | — | — | — | **inconclusive** |
| embed_count_per_task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| abstain_rate | 33.3% [5.7%, 60.9%] | 100.0% [100.0%, 100.0%] | — | **chorusgraph** |

Paired tasks: **12** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 9 metrics, LangGraph wins 3 metrics)

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| latency_ms_p50 | 12937.00 [6331.50, 14964.50] | 9.50 [9.00, 5762.00] | — | **chorusgraph** |
| latency_ms_p95 | 17134.95 [14644.45, 19561.00] | 17980.80 [4882.00, 18841.00] | — | **langgraph** |
| latency_ms_mean | 11410.75 [8549.55, 14020.56] | 4291.33 [968.08, 8277.82] | -7119.4167 [-11259.8833, -2577.5104] | **chorusgraph** |
| cost_usd_per_task | 0.0003 [0.0002, 0.0004] | 0.0001 [0.0000, 0.0002] | -0.0002 [-0.0004, -0.0001] | **chorusgraph** |
| llm_calls_per_task | 3.83 [3.00, 4.67] | 1.50 [0.33, 2.83] | -2.3333 [-3.5000, -1.0000] | **chorusgraph** |
| tokens_in_per_task | 815.67 [482.89, 1127.01] | 252.00 [39.42, 506.92] | — | **chorusgraph** |
| tokens_out_per_task | 328.92 [238.82, 417.51] | 93.67 [24.75, 174.42] | — | **chorusgraph** |
| tool_calls_per_task | 0.8333 [0.4167, 1.2500] | 0.3333 [0.0000, 0.8333] | — | **chorusgraph** |
| task_success_rate | 58.3% [36.0%, 80.7%] | 66.7% [47.1%, 86.2%] | — | **chorusgraph** |
| error_rate | 0.0% [0.0%, 24.2%] | 0.0% [0.0%, 24.2%] | — | **tie** |
| cache_hit_rate | 0.0% [0.0%, 24.2%] | 58.3% [36.0%, 80.7%] | — | **chorusgraph** |
| llm_calls_on_cache_hit_mean | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| embed_count_per_task | 0.0000 [0.0000, 0.0000] | 1.50 [0.33, 2.83] | — | **langgraph** |
| abstain_rate | 16.7% [0.0%, 44.8%] | 0.0% [0.0%, 24.2%] | — | **langgraph** |

Paired tasks: **12** (same task/case IDs)
