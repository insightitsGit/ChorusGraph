# Handoffback E2 — Resilience

**Status:** Complete on branch `P1_Enterprice1`  
**Depends on:** E1 (`f80655b`)

## Summary

E2 adds a unified resilience layer: typed errors, exponential-backoff retries, per-service circuit breakers, idempotent digest writes, and graceful node failure handling with partial results recorded in the Route Ledger.

## File tree

```
chorusgraph/resilience/
  __init__.py
  errors.py
  circuit_breaker.py
  policy.py
  executor.py
  idempotency.py
  partial.py
chorusgraph/core/channels.py      # NodeUpdate error fields
chorusgraph/core/scheduler.py     # _failure_command on node exception
chorusgraph/core/trace.py         # ledger error fields
chorusgraph/ledger/models.py
chorusgraph/ledger/sink.py
chorusgraph/nodes/tool.py
chorusgraph/examples/finance_agent/gemini_client.py
chorusgraph/memory/async_digest.py
tests/test_resilience.py
handoffs/handoffbackE2.md
```

## How to run

```powershell
pytest tests/test_resilience.py -v
pytest   # full deterministic suite
```

## Decisions

| Topic | Choice | Why |
|-------|--------|-----|
| Circuit breaker | **In-process registry** (no external lib) | Zero deps; sufficient for single-process engine |
| Retry defaults | 2 retries, 0.25s base, 2× backoff | Matches prior tool.py behavior |
| Partial results | `Command(goto=END)` + `__partial__` / `__node_error__` in state | Graph completes; caller inspects error artifact |
| Idempotency | In-process `IdempotencyGuard` on digest `source_id` | Prevents duplicate Cortex writes on retry |

## Answers to handoff §5

1. **Breaker:** Custom in `chorusgraph/resilience/circuit_breaker.py`; opens after 5 failures, 30s recovery.
2. **Partial contract:** `PartialRunResult` + state keys `__partial__`, `__errors__`, `__node_error__`; ledger `error_code/kind/retryable`.
3. **Most fragile before:** Uncaught node exceptions in `_invoke_node`; tool retries without breaker.
4. **Proposed E3:** Tool sandbox + allowlists, TLS default, federation auth, cache isolation, PII redaction, CI SAST/SCA.

## Blockers

None for E2.

## Next

**E3 — Security** on `P1_Enterprice1`.
