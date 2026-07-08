# Benchmark Latency & LLM Calls Summary (Post-Fix)

Runs after prompt (`annual_rate_pct`) and fair success-rate comparison fixes.
All values are **mean per task** with 95% CI in brackets. Latency in **milliseconds**.

## Light tier — `light_20260708_101409` (40 paired tasks/scenario)

| Scenario | Engine | Success | LLM calls/task | Mean latency | p50 latency | p95 latency | Cache hit | Tokens in | Tokens out |
|----------|--------|---------|----------------|--------------|-------------|-------------|-----------|-----------|------------|
| FL1 vs FC1 | LangGraph | 82.5% | 3.35 [2.98, 3.75] | 4949 [4174, 5873] | 3811 [3602, 4240] | 12123 [7724, 14083] | 0.0% | 1149 [1016, 1291] | 255 [227, 285] |
| FL1 vs FC1 | ChorusGraph | **100.0%** | **0.93 [0.60, 1.25]** | **1393 [872, 1969]** | **44 [23, 2409]** | **4718 [2654, 6698]** | **47.5%** | **334 [211, 469]** | **73 [46, 104]** |
| FL2 vs FC2 | LangGraph | 90.0% | 2.08 [2.00, 2.17] | 3114 [2517, 3820] | 2356 [2217, 2458] | 8524 [3265, 11178] | 0.0% | 586 [527, 645] | 125 [116, 135] |
| FL2 vs FC2 | ChorusGraph | **95.0%** | **0.70 [0.50, 0.90]** | **1016 [681, 1383]** | **1150 [13, 1305]** | **2448 [1630, 5195]** | **40.0%** | **158 [115, 202]** | **52 [38, 67]** |
| HL1 vs HC1 | LangGraph | 70.0% | 3.08 [2.80, 3.38] | 7309 [6034, 8762] | 6005 [5133, 8383] | 12198 [11354, 23235] | 0.0% | 972 [851, 1101] | 331 [296, 371] |
| HL1 vs HC1 | ChorusGraph | 70.0% | **1.95 [1.65, 2.27]** | **4627 [3879, 5467]** | **3549 [3217, 4163]** | **10939 [6532, 11896]** | **42.5%** | 1175 [971, 1410] | **191 [147, 235]** |
| HL2 vs HC2 | LangGraph | 57.5% | 3.83 [3.35, 4.28] | 10477 [8986, 11972] | 11534 [9663, 13450] | 16391 [15540, 19467] | 0.0% | 858 [694, 1025] | 295 [252, 340] |
| HL2 vs HC2 | ChorusGraph | **90.0%** | **3.50 [3.00, 4.00]** | 10854 [9088, 12629] | 11722 [7919, 14024] | 18348 [17380, 21351] | **25.0%** | 1051 [835, 1267] | **265 [221, 310]** |

### Light tier — ChorusGraph savings vs LangGraph (Δ)

| Scenario | Δ LLM calls | Δ mean latency (ms) | Δ p50 (ms) | Δ p95 (ms) |
|----------|-------------|---------------------|------------|------------|
| FL1/FC1 | **−2.43** | **−3556** | **−3768** | **−7406** |
| FL2/FC2 | **−1.38** | **−2098** | **−1206** | **−6077** |
| HL1/HC1 | **−1.13** | **−2681** | **−2456** | **−1259** |
| HL2/HC2 | −0.33 | +378 | +188 | +1957 |

---

## Mid tier — `mid_20260708_111539` (100 paired tasks/scenario)

| Scenario | Engine | Success | LLM calls/task | Mean latency | p50 latency | p95 latency | Cache hit | Tokens in | Tokens out |
|----------|--------|---------|----------------|--------------|-------------|-------------|-----------|-----------|------------|
| FL1 vs FC1 | LangGraph | 87.0% | 3.24 [3.01, 3.49] | 4760 [4332, 5243] | 3801 [3673, 4275] | 9025 [7845, 12802] | 0.0% | 1116 [1035, 1199] | 252 [232, 273] |
| FL1 vs FC1 | ChorusGraph | **98.0%** | **0.77 [0.58, 0.97]** | **1348 [970, 1753]** | **31 [24, 258]** | **6280 [3149, 6943]** | **52.0%** | **271 [199, 343]** | **59 [43, 75]** |
| FL2 vs FC2 | LangGraph | 87.0% | 2.03 [1.99, 2.07] | 3269 [2898, 3689] | 2581 [2474, 2701] | 8834 [4208, 11025] | 0.0% | 583 [542, 622] | 119 [114, 126] |
| FL2 vs FC2 | ChorusGraph | **94.0%** | **0.69 [0.57, 0.82]** | **1085 [839, 1364]** | **1155 [26, 1273]** | **3445 [2035, 5437]** | **40.0%** | **157 [129, 185]** | **52 [43, 62]** |
| HL1 vs HC1 | LangGraph | 74.0% | 3.00 [2.83, 3.17] | 7036 [6237, 7862] | 5997 [5349, 7152] | 14544 [11132, 21331] | 0.0% | 926 [851, 1004] | 320 [298, 344] |
| HL1 vs HC1 | ChorusGraph | **79.0%** | **1.56 [1.42, 1.72]** | **3990 [3553, 4553]** | **3351 [3196, 3588]** | **7564 [5633, 9193]** | **60.0%** | 963 [875, 1063] | **138 [116, 161]** |
| HL2 vs HC2 | LangGraph | 59.0% | 3.82 [3.53, 4.11] | 10296 [9254, 11268] | 10709 [9638, 11528] | 17478 [16563, 18370] | 0.0% | 825 [721, 928] | 290 [262, 317] |
| HL2 vs HC2 | ChorusGraph | **85.0%** | **3.15 [2.82, 3.48]** | 10753 [9541, 11959] | 10913 [7541, 13215] | 19022 [18057, 21513] | **51.0%** | 986 [850, 1110] | **228 [202, 256]** |

### Mid tier — ChorusGraph savings vs LangGraph (Δ)

| Scenario | Δ LLM calls | Δ mean latency (ms) | Δ p50 (ms) | Δ p95 (ms) |
|----------|-------------|---------------------|------------|------------|
| FL1/FC1 | **−2.47** | **−3412** | **−3770** | **−2745** |
| FL2/FC2 | **−1.34** | **−2184** | **−1427** | **−5389** |
| HL1/HC1 | **−1.44** | **−3046** | **−2646** | **−6980** |
| HL2/HC2 | **−0.67** | +456 | +204 | +1544 |

---

## Headline takeaways

1. **Finance (FL1/FL2):** ChorusGraph cuts LLM calls ~65–76% and mean latency ~67–72% vs LangGraph, driven by 40–52% cache hit rates.
2. **Healthcare single (HL1):** ~48% fewer LLM calls, ~43% lower mean latency; success +5pp on mid tier.
3. **Healthcare multi (HL2):** ChorusGraph wins on success (+26pp mid) and fewer LLM calls, but mean/p95 latency remain comparable or slightly higher (multi-agent + Cortex embeds).
4. **Cache hits = zero LLM calls** on finance scenarios; healthcare cache hits still incur ~1–2 LLM calls (abstain/validation path).

## Source reports

- `benchmark/results/azure_light_20260708_101409/mvp_scenarios/light_20260708_101409/COMPARISON_REPORT.md`
- `benchmark/results/azure_mid_20260708_111539/mvp_scenarios/mid_20260708_111539/COMPARISON_REPORT.md`

Heavy post-fix run: `heavy_20260708_124337` (in progress at time of writing).
