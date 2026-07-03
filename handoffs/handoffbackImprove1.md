# handoffbackImprove1.md — Improve-1 implementation return

**Date:** 2026-07-03  
**Engineer:** Cursor  
**Baseline:** 206 passed → **245 passed**, 3 skipped

## T1 — Per-node pending writes ✅

**Files:** `chorusgraph/core/pending_writes.py`, `chorusgraph/core/persistence.py`, `chorusgraph/core/scheduler.py`, `tests/test_pending_writes.py`

**Exit criteria:** PASS — parallel A/B/C crash-resume test in `tests/test_pending_writes.py`

```text
pytest tests/test_pending_writes.py tests/test_engine_phases.py -q → 14 passed
pytest tests/ -q → 245 passed
```

## T2 — Command + interrupt-returns-value ✅

**Files:** `chorusgraph/core/node.py`, `chorusgraph/core/ir.py`, `chorusgraph/core/scheduler.py`, `tests/test_command_interrupt.py`

**Exit criteria:** PASS — Command routing, undeclared goto error, interrupt round-trip

## T3 — Send dynamic fan-out ✅

**Files:** `chorusgraph/core/send.py`, `chorusgraph/core/scheduler.py`, `chorusgraph/core/graph.py`, `chorusgraph/core/ir.py`, `chorusgraph/core/node.py`, `chorusgraph/core/trace.py`, `tests/test_send.py`

**Mechanics:** `Send(target, payload)`, dedup (exact + projector coarse 0.88), join policies (`all`, `quorum`, `timeout` clock), `max_branches`, branch pending writes, ledger `send_batch` events

**Exit criteria:** PASS — all tests in `tests/test_send.py`

## T4 — Subgraphs (local) ✅

**Files:** `chorusgraph/core/subgraph.py`, `chorusgraph/core/graph.py` (`add_subgraph`), `chorusgraph/core/trace.py`, `chorusgraph/ledger/models.py`, `tests/test_subgraph.py`

**Notes:**
- Child `thread_id` = `{parent}__{node}` (Windows-safe; handoff `:` adapted)
- `BoundaryTranslator.translate(PrismState) -> str` — optional re-project at boundary
- Nested ledger: `parent_run_id`, `subgraph_node` on `LedgerStep`
- Subgraph cache skip via `CachePolicy` on `add_subgraph`

## T5 — Remote subgraph contract ✅ (in-memory)

**Files:** `chorusgraph/core/subgraph_transport.py`, `chorusgraph/transport/prismapi.py`, `tests/test_subgraph_remote.py`

**Honesty:** encode/route/decode round-trip only; **no network latency numbers**. Real wiring = P5/P6 debt.

## T6 — ChorusBatchFrame ✅ (contract)

**Files:** `chorusgraph/transport/chorus.py`, `tests/test_chorus_batch.py`

**Shape:** `(N, 64)` float32 batch + artifact refs; property test on bytes round-trip

## T7 — Functional API ✅

**Files:** `chorusgraph/func.py`, `tests/test_func_api.py`

Sugar only — builds `Graph` IR; no engine changes beyond existing Send/node paths

## T8 — Compat adapters ✅

**Files:**
- `tests/compat/test_conformance.py` + `test_run_conformance.py` (10 patterns)
- `chorusgraph/compat/checkpoint_import.py` (CLI)
- `chorusgraph/compat/tool_node.py`
- `chorusgraph/compat/otel_exporter.py`
- `tests/compat/test_adapters.py` (MCP probe skips if `PrismAPIMCPServer` unavailable)

## Benchmark (post T3+T4) ✅

**Files:** `benchmark/scenarios_fanout.py`, `tests/test_benchmark_fanout.py`

**Measured (offline stub, same fixture):**

| Metric | Value |
|--------|-------|
| branches_requested | 3 |
| branches_executed | 2 |
| llm_calls | 1 |
| wall_ms | ≥ 0 (runtime-dependent) |

Run: `python -m pytest tests/test_benchmark_fanout.py -q`

## Prism signature deviations

| Symbol | Handoff | Actual |
|--------|---------|--------|
| `JsonFileCheckpointer.put_writes` | wire | no-op — ChorusGraph `PendingWriteStore` owns JSON pending writes |
| `AsyncPostgresCheckpointer.aput_writes` | wire | NotImplementedError — delegated when available |
| `BoundaryTranslator.translate` | envelope in/out | `(PrismState) -> str` — adapted at subgraph boundary |
| Subgraph thread_id | `parent:node` | `parent__node` (filesystem-safe on Windows) |

## LangGraph grep gate

```bash
rg -n langgraph chorusgraph/{core,checkpoint,compat,transport}
# Only compat/langgraph.py shim references (expected)
```

## Full suite

```bash
python -m pytest tests/ -q
# 245 passed, 3 skipped
```

No git commit (per Director rule).
