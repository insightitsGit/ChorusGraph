# ADR-007: ReAct `stop_on_repeated_action` default on

**Status:** Accepted · shipped  
**Date:** 2026-07-17  
**Related:** [`LOOP-TOKEN-BURN-FINDINGS.md`](LOOP-TOKEN-BURN-FINDINGS.md), [`ADR-006-l1-single-flight.md`](ADR-006-l1-single-flight.md)

## Context

Stuck ReAct agents can re-emit the **same** tool+args until `max_steps`. That is bounded wallet burn (defaults still cap steps), but wasteful. TokenShield-style unique-arg thrash is a different problem and remains capped by `max_steps` only.

## Decision

Change `ReActOpts.stop_on_repeated_action` default from `False` → **`True`**.

- **Semantics unchanged:** exact `(tool, json.dumps(args, sort_keys=True))` seen twice → `finish_reason=repeated_action`.
- **Opt out:** `ReActOpts(stop_on_repeated_action=False)` when the app *intends* to call the same tool+args more than once (e.g. refresh).
- **Not misleading:** this does **not** stop unique args each hop; docs state that clearly. L1 cache is unrelated.

## Consequences

- Safer default for identical thrash; intentional retries must opt out.
- Tests: `tests/test_agent.py` (`test_stop_on_repeated_action_*`).
- Docs: `DEVELOPER_GUIDE.md` §11.

---
*ADR-007 · 2026-07-17*
