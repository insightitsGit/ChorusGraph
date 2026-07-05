# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Healthcare Multi (HL2 vs HC2)

**Overall:** langgraph (Chorus wins 5 metrics, LangGraph wins 7 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 70.0% [58.1%, 81.9%] | 85.0% [77.1%, 92.9%] | — |
| LLM calls / task | 3.85 [3.38, 4.33] | 3.45 [2.95, 3.95] | -0.4000 [-0.7000, -0.1500] |
| Mean latency | 10554.15 [8923.38, 12196.77] | 11504.15 [9628.85, 13409.29] | 950.00 [-119.10, 2065.89] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 30.0% [14.6%, 45.4%] | — |
| Abstain rate | 10.0% [0.0%, 23.1%] | 0.0% [0.0%, 8.8%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 70.0% [58.1%, 81.9%] | 85.0% [77.1%, 92.9%] | — | **chorusgraph** |
| LLM calls / task | 3.85 [3.38, 4.33] | 3.45 [2.95, 3.95] | -0.4000 [-0.7000, -0.1500] | **chorusgraph** |
| Mean latency | 10554.15 [8923.38, 12196.77] | 11504.15 [9628.85, 13409.29] | 950.00 [-119.10, 2065.89] | **langgraph** |
| Latency p50 | 11332.50 [9714.00, 13183.00] | 12497.00 [8036.00, 13688.70] | — | **langgraph** |
| Latency p95 | 16968.95 [16020.55, 23657.00] | 22686.60 [18734.35, 24666.00] | — | **langgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0003 [0.0003, 0.0004] | 0.0000 [-0.0000, 0.0000] | **langgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 30.0% [14.6%, 45.4%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 2.50 [1.75, 3.25] | — | **inconclusive** |
| Tokens in / task | 882.52 [705.15, 1057.48] | 1076.03 [853.09, 1296.68] | — | **langgraph** |
| Tokens out / task | 301.82 [250.19, 355.37] | 261.20 [218.07, 306.10] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.7500 [0.5250, 0.9750] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 8.90 [7.90, 9.90] | — | **langgraph** |
| Abstain rate | 10.0% [0.0%, 23.1%] | 0.0% [0.0%, 8.8%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)
