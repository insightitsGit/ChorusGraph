# Runbook: LLM errors (E4)

**Symptom:** Graph returns `__partial__` with `error_code` rate_limit or auth.

**Diagnose:**
1. Check Route Ledger step: `error_code`, `error_kind`, `retryable`.
2. Metrics: `GET /metrics` → `errors` counter.
3. Trace: `ledger_to_trace(last_ledger)` — span attrs on failed node.

**Mitigate:** Verify `GEMINI_API_KEY`, reduce concurrency, E2 breaker will open after repeated failures.

# Runbook: Tool timeout

**Symptom:** Tool node `error_code=timeout` in ledger.

**Diagnose:** Frankfurter or custom tool latency; check `duration_ms` on ledger step.

**Mitigate:** Increase `ToolSpec.timeout_seconds` or fix upstream service.

# Runbook: Cache miss storm

**Symptom:** High `cache_misses`, low hit rate in `/metrics`.

**Diagnose:** Compare cache_score in ledger spans; verify seed policy.

**Mitigate:** Warm cache via quality-gated seed; review paraphrase keying.

# Runbook: DB down

**Symptom:** Checkpoint or ledger write failures; readiness `/ready` false when hook configured.

**Mitigate:** Restore Postgres/SQLite; run E5 migration forward.
