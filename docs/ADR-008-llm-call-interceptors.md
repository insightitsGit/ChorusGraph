# ADR-008: LLM call interceptors (provider boundary)

**Status:** Accepted · shipped in **1.3.0**  
**Date:** 2026-07-18  
**Related:** PrismShine INTEGRATION.md §1 · [`LOOP-TOKEN-BURN-FINDINGS.md`](LOOP-TOKEN-BURN-FINDINGS.md) · ADR-007

## Context

PrismShine needs **pre-generation** Tier-0 forensics (halt before tokens) and **post-generation** verify around LLM calls. A naive BSP wrap of `fn(ctx)` is the wrong boundary: preload is resolved *inside* the node, and non-LLM nodes would fire falsely.

## Decision

Ship an **LLM call port** plus optional hooks:

```python
compiled.bind_llm(model).register_interceptor(before_llm=..., after_llm=...)
# Inside a generator node:
text = ctx.call_llm(system, user)
```

| API | Role |
|-----|------|
| `InterceptDecision.proceed / halt / reroute` | Hook outcomes |
| `CompiledGraph.register_interceptor(...)` | Register hooks (inert until `call_llm`) |
| `CompiledGraph.bind_llm(model)` | Default model for `call_llm` |
| `NodeContext.call_llm(system, user)` | Provider boundary — hooks fire here |

- **Halt** → `NodeInterrupt` with `{"reason": "llm_intercept_halt", "fallback": ...}`
- **Reroute** → validated `Command(goto=hop)` (respects recursion / graph edges)
- Graphs that never call `call_llm` behave exactly as 1.2.0
- PrismShine **shine_node** remains the guaranteed node-based fallback

## Streaming (future)

`call_llm` can grow a streaming variant later without changing BSP scheduling (PrismShine DESIGN §12.4). No streaming hooks in 1.3.0.

## Consequences

- Code: `chorusgraph/core/intercept.py`, `NodeContext.call_llm`, scheduler wiring
- Tests: `tests/test_llm_interceptors.py`
