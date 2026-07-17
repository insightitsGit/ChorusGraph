# Architecture — ChorusGraph

ChorusGraph is a **native agent-graph runtime**. Full composition: [COMPOSE.md](COMPOSE.md). AI summary: [ai-overview.md](ai-overview.md).

## Stack placement

```
┌─────────────────────────────────────────────────────────────┐
│  Your graph — nodes, edges, conditional routing              │
├─────────────────────────────────────────────────────────────┤
│  ChorusStack — swappable ports                               │
│  ┌──────────┬──────────┬──────────┬──────────────────────┐  │
│  │ Cache    │ Memory   │ Tools    │ Retrieval (L2)       │  │
│  │ Prism /  │ Cortex   │ Registry │ Keyword / PrismRAG   │  │
│  │ Redis    │          │          │                      │  │
│  └──────────┴──────────┴──────────┴──────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Engine (fixed): BSP scheduler · envelopes · Resonance · JL  │
├─────────────────────────────────────────────────────────────┤
│  Route Ledger · checkpoints · tenant guards · observability  │
└─────────────────────────────────────────────────────────────┘
```

Optional: [PrismGuard](https://github.com/insightitsGit/PrismGuard) as a separate package in front of LLM hops (not a ChorusStack port).

## Related

- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) · [PLUGINS.md](PLUGINS.md) · [ADR-005-warm-chunk-vectors.md](ADR-005-warm-chunk-vectors.md) · [ADR-006-l1-single-flight.md](ADR-006-l1-single-flight.md) · [ADR-007-react-repeated-action-default.md](ADR-007-react-repeated-action-default.md)
- [llm-context.md](llm-context.md) · [TERMINOLOGY.md](TERMINOLOGY.md)
