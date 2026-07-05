# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Healthcare Multi (HL2 vs HC2)

**Overall:** langgraph (Chorus wins 2 metrics, LangGraph wins 9 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 50.0% [35.2%, 64.8%] | 90.0% [84.0%, 96.0%] | — |
| LLM calls / task | 3.83 [3.38, 4.28] | 3.92 [3.45, 4.42] | 0.1000 [0.0250, 0.2000] |
| Mean latency | 10596.20 [9018.24, 12192.30] | 12660.05 [10733.33, 14601.35] | 2063.85 [1230.67, 2921.51] |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — |
| Abstain rate | 12.5% [0.0%, 26.1%] | 2.5% [0.0%, 12.9%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 50.0% [35.2%, 64.8%] | 90.0% [84.0%, 96.0%] | — | **chorusgraph** |
| LLM calls / task | 3.83 [3.38, 4.28] | 3.92 [3.45, 4.42] | 0.1000 [0.0250, 0.2000] | **langgraph** |
| Mean latency | 10596.20 [9018.24, 12192.30] | 12660.05 [10733.33, 14601.35] | 2063.85 [1230.67, 2921.51] | **langgraph** |
| Latency p50 | 11056.50 [8745.50, 13157.50] | 14277.50 [9921.00, 16178.50] | — | **langgraph** |
| Latency p95 | 19382.55 [15177.60, 22080.00] | 21238.75 [18415.85, 25604.00] | — | **langgraph** |
| Cost / task | 0.0003 [0.0002, 0.0004] | 0.0003 [0.0003, 0.0004] | 0.0000 [-0.0000, 0.0001] | **langgraph** |
| Cache hit rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| LLM calls on cache hit | — | — | — | **inconclusive** |
| Tokens in / task | 836.85 [670.34, 995.88] | 1130.97 [902.96, 1342.21] | — | **langgraph** |
| Tokens out / task | 294.27 [244.00, 349.04] | 278.12 [244.34, 311.30] | — | **chorusgraph** |
| Tool calls / task | 0.8750 [0.6500, 1.1000] | 0.9000 [0.6750, 1.1256] | — | **langgraph** |
| Error rate | 0.0% [0.0%, 8.8%] | 0.0% [0.0%, 8.8%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 9.88 [8.92, 10.88] | — | **langgraph** |
| Abstain rate | 12.5% [0.0%, 26.1%] | 2.5% [0.0%, 12.9%] | — | **langgraph** |

Paired tasks: **40** (same task/case IDs)
