# Fair baseline — Container E (LangGraph finance multi-agent)

**Purpose:** Competent LangGraph multi-agent finance baseline — same domain, workload, tools, and scoring as A/B.

## Pipeline (fixed 4-hop)

```
researcher → tool → writer → validator
```

| Hop | Role | LLM? | Tools? |
|-----|------|------|--------|
| researcher | Plan tools + intent | Yes | No |
| tool | Execute registry calls | No | Yes (code) |
| writer | Draft answer | Yes | No |
| validator | Rate/FV check + rewrite | Optional | No |

## Handoff model (E)

**Growing text context** — each hop appends to `context` string (LangGraph baseline, analogous to Container C healthcare).

## Parity with Container F

| Dimension | E | F |
|-----------|---|---|
| Workload | `benchmark/workload.py` | Same |
| Tools | `default_finance_registry()` | Same |
| Scoring | `score_task_success` / `rubric.py` | Same |
| Model | `InstrumentedGeminiClient` | Same |
| Cache | None | Semantic cache_gate (like B) |
| Cortex | None | Yes (memory tasks, like B) |
| Handoffs | Growing text `context` | Envelope + compact `hop_input` |
| Extra hops | None | vector_ingress, cache_gate |

## Parity with Container A

| Dimension | A (single-agent) | E (multi-agent) |
|-----------|------------------|-----------------|
| Framework | LangGraph ReAct loop | LangGraph linear pipeline |
| Cache/Cortex | None | None |
| Tool execution | ReAct tool node | Dedicated tool hop |
| Fair comparison | A vs B single-agent | **E vs F multi-agent** |

## Verification

```powershell
python -m pytest tests/test_finance_multiagent.py -q
python -m benchmark.run_finance_multiagent --tasks 60 --band 40 --output-dir benchmark/results/h14_finance_multiagent
```

*Fair baseline E · H14 · finance multi-agent LangGraph · no cache.*
