# ADR-006: L1 single-flight coalescing (in-flight cache miss join)

**Status:** Accepted · **shipped opt-in** (default off)  
**Date:** 2026-07-17  
**Related:** [`CACHE_PROFILES.md`](CACHE_PROFILES.md), [`DESIGN_v0.3_PRISM_ENGINE.md`](DESIGN_v0.3_PRISM_ENGINE.md) §4.2, [`LOOP-TOKEN-BURN-FINDINGS.md`](LOOP-TOKEN-BURN-FINDINGS.md)

## Context

L1 (`cache_gate` / PrismCache) helps when a verified answer **already exists**. It does **not** help when User A is still computing and User B arrives with the **same** cache key before A seeds L1 (cache stampede).

This is **not** the TokenShield unique-loop problem — see [`LOOP-TOKEN-BURN-FINDINGS.md`](LOOP-TOKEN-BURN-FINDINGS.md).

### Sameness (strict)

| Allowed | Not allowed (v1) |
|---------|------------------|
| `keying` ∈ {`exact`, `fingerprint`} | `semantic` |
| `scope` ∈ {`global`, `tenant`} | `user`, `session` |

## Decision

Opt-in single-flight: one **leader** runs the miss path; **followers** with the same flight key wait (or time out and compute independently).

**Default off** — existing graphs keep parallel-miss latency unless they opt in.

### Flight key

```text
sha256(tenant_id | scope_id | category_slug | keying | direct_key)
```

### Shipped placement

| Layer | Role |
|-------|------|
| `chorusgraph/cache_gate/flight.py` | `FlightPolicy`, `flight_eligible`, `InProcessFlightCoordinator` |
| `CacheInterceptor.run_miss` / `arun_miss` | Join when eligible |
| `_invoke_node` / `_ainvoke_node` | Miss body goes through interceptor |
| `CacheProfile.single_flight` | Per-profile opt-in |
| `ChorusStack.with_flight(...)` | Runtime-wide opt-in |

### Latency

Leader ≈ unchanged. Followers wait instead of a second paid call. Timeout / interrupt → fallthrough.

## Enable

```python
from chorusgraph.cache_gate import FlightPolicy
from chorusgraph.sections.models import CachePolicy, CacheProfile

# Per node
CacheProfile(keying="exact", scope="global", single_flight=True)

# Or stack-wide
stack = ChorusStack.defaults().with_flight(FlightPolicy(enabled=True, join_timeout_s=30.0))
```

## Non-goals / backlog

- Semantic coalescing
- Distributed Redis flight map (multi-replica)
- Ledger `flight_*` events

## Tests

`tests/test_l1_single_flight.py`

---
*ADR-006 · shipped opt-in 2026-07-17*
