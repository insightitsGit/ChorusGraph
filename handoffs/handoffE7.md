# Handoff E7 — Performance & Load

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/ENTERPRISE_READINESS.md`](../docs/ENTERPRISE_READINESS.md) **§E7** · [`../docs/PROCESS.md`](../docs/PROCESS.md).
**Depends on:** E1, E5, E6. **Return in:** `handoffs/handoffbackE7.md`.

This is the **separate load/traffic test** the Director said they'd design — coordinate the workload with them. It is
distinct from the H9 per-task A/B benchmark (that measures cost/latency/accuracy; this measures throughput under load).

## 0. Operating rules
No fakes; real load. One bounded increment. Report honest numbers — throughput ceilings and failure points, not just happy-path.

## 1. Goal
A documented throughput + latency envelope under **sustained concurrent load**, with no leaks.

## 2. Deliverables
- **Load/throughput test harness** (e.g. locust / k6) — concurrent sessions, sustained load, ramp.
- **Soak test** — memory/leak profiling over a long run.
- **Capacity characterization** — where it saturates, connection-pool behavior, degradation curve.
- (Reference the H9/H10 per-task benchmark — do not repeat it here.)

## 3. Out of scope
E1–E6 · E8–E9 · the per-task A/B (H9/H10) · MVP fixes.

## 4. Acceptance criteria
- [ ] Documented **throughput** + P50/P95 latency under sustained concurrent load, at increasing concurrency.
- [ ] **No memory leaks** over a soak test (flat memory profile).
- [ ] A documented **capacity envelope** (where it saturates and how it degrades).
- [ ] Coordinated workload/SLOs signed off by the Director.

## 5. Open questions for handoffbackE7
1. Load tool + target SLOs (agreed with Director).
2. Test environment (Azure sizing).
3. Saturation point + the bottleneck (LLM, DB, CPU, Cortex).
4. Proposed E8 scope.

## 6. Return format
Summary · file tree · how to run · load/soak results (throughput, latency, memory profile) · decisions/deviations · blockers · answers to §5 · proposed E8.

---
*Handoff E7 · enterprise track · load/throughput + soak · gate to any scale claim.*
