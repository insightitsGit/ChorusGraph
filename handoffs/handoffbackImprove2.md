# Handoff back — Improve-2 (P5/P6 absorbed)

**Date:** 2026-07-03 · **Engineer:** Cursor · **Status:** All tasks T1–T8 implemented

---

## Summary

Improve-2 is complete: ChorusStack hygiene (T1/T2), Send isolation + LangGraph compat (T3/T4), real distribution/federation wiring (T5–T7), and measured loopback proof (T8). Full suite: **271 passed, 1 skipped** (`test_bus_redis` two-process test skips unless `CHORUSGRAPH_REDIS_URL` points at a live Redis).

---

## T1 — ChorusStack: no hardcoded thresholds

**Files:** `chorusgraph/compose/stack.py`, `chorusgraph/cache_gate/thresholds.py`, `chorusgraph/core/cache_interceptor.py`, `benchmark/thresholds.py` (re-export)

**Exit:** PASS — `tests/test_compose_stack.py::test_stack_default_thresholds_from_measured`, `test_stack_explicit_thresholds_override`

Coarse/verify default to `None`; `to_cache_runtime()` resolves coarse from `measured_thresholds()`; per-slug verify via `CacheRuntime.verify_threshold_for(slug)` unless explicit `verify_threshold` override on stack.

---

## T2 — ChorusStack.with_cache via dataclasses.replace

**Files:** `chorusgraph/compose/stack.py`

**Exit:** PASS — `tests/test_compose_stack.py::test_with_cache_preserves_all_fields`

**with_cache cached-runtime bug:** **YES — existed.** Hand-copied constructor omitted `_cache_runtime`, so a cache swap could keep a stale `CacheRuntime` pointing at the old backend. Fixed with `dataclasses.replace(self, cache=backend, _cache_runtime=None)`.

---

## T3 — Branch same-key isolation

**Files:** `chorusgraph/core/channels.py`, `chorusgraph/core/send.py`, `chorusgraph/core/scheduler.py`, `tests/test_send.py`

**Exit:** PASS — `test_branch_same_key_isolation_and_scalar_collision`

- Documented `BRANCH_SCALAR_COLLISION_RULE = "last_by_sorted_branch_id"` for scalar keys during sequential branch apply.
- Append-list keys (`hop_metrics`, etc.) accumulate all branch contributions.
- `SendBatch.parent_snapshot` freezes pre-fan-out state so branches do not see sibling writes mid-step.
- Resume restores `resumed_branch_ids` + `parent_snapshot` from checkpoint metadata.

---

## T4 — Compat Send-from-conditional-edge

**Files:** `chorusgraph/compat/langgraph.py`, `tests/compat/test_conformance.py`, `tests/compat/test_run_conformance.py`

**Exit:** PASS — `test_conformance_pattern_compiles_and_runs[langgraph_send_edge]`

Mirrors LangGraph conditional edges: when router returns `langgraph.types.Send` (`.node`/`.arg`), dispatch caches sends and routes to synthesized `__lg_send_split__*` node; join=`all` auto-set on reduce targets.

---

## T5 — RedisBroadcast two-process bus

**Files:** `chorusgraph/core/bus.py` (unchanged API), `tests/test_bus_redis.py`

**Exit:** PASS (inproc) / SKIP without Redis — `test_inproc_routing_deterministic`; `test_redis_broadcast_two_process_visibility` skips unless `CHORUSGRAPH_REDIS_URL` set.

### prism.* signatures (inspected)

```text
RedisBroadcast(redis_url: str = 'redis://localhost:6379/0', redis_key: str = 'prismresonance:frequencies', ttl: Optional[int] = None)
  .register_agent(node_id, freq)
  .set_frequency(node_id, freq)
  .broadcast(freq)
  .dominant_frequency() / .get_frequencies()
```

Requires `pip install redis` for `RedisBroadcast` construction.

---

## T6 — CHORUS mesh transport

**Files:** `chorusgraph/transport/chorus.py`, `chorusgraph/core/transport_router.py`, `tests/test_transport_chorus.py`

**Exit:** PASS — wire round-trip + HTTP loopback via `ClusterTransport`

### prism.* signatures (inspected)

```text
ClusterTransport(node_id: str, peers: dict[str, str], *, mode: TransportMode = DIRECT, on_frame: Optional[FrameHandler] = None)
  async publish(frame: dict[str, Any]) -> None   # POST {peer}/chorus/ingest
  async handle_incoming(frame) / status() / close()
```

`ChorusBatchFrame.to_wire_dict()` / `from_wire_dict()` is the on-wire unit (base64 float32 payload). `ChorusSpine.deliver_batch()` calls `ClusterTransport.publish()` when `client` is set.

---

## T7 — PrismAPI federation + Send-over-transport

**Files:** `chorusgraph/transport/prismapi.py`, `chorusgraph/core/subgraph_transport.py`, `chorusgraph/core/scheduler.py`, `tests/test_federation.py`

**Exit:** PASS — remote batch (1 frame), quorum-8 join, zero re-embed on `query_vector`

### prism.* signatures (inspected)

```text
PrismAPIProvider(projector, embedder, semantic_fields, id_field=..., exact_fields=..., provider_id=...)
  .expose(fn) / .as_chorus_frame(result_dicts) / ._invoke_handler(query_text, query_vector, top_k)

PrismAPIClient(projector, embedder, loopback_provider=..., host=..., port=..., chorus_path=...)
  .query(query_text, top_k=...)      # consumer embeds query once
  .query_vector(query_vector, ...)   # zero embedding calls
  ._loopback_exchange(req_frame, context)
```

**BoundaryTranslator:** Not found in `prism.bridge.vector` (handoff assumed name). Boundary re-projection uses `PrismProjector.project()` at `PrismAPISpine.route_envelope()` when `boundary_translator` is set.

**Send-over-transport:** Remote subgraph (`location="chorus"|"prismapi"`) + `Send` to subgraph node → `_execute_remote_send_batch()` sends one `ChorusBatchFrame` via `TransportRouter.deliver_batch()`, respects quorum join, fans results into `branch_outputs`.

---

## T8 — Measured distributed proof (LOOPBACK)

**Files:** `benchmark/distributed_proof.py`, `benchmark/results/distributed_proof/`

**Environment:** Windows-11, Python 3.12.10, host DESKTOP-H3RO1EI, tier **LOOPBACK** (not Azure multi-VM)

| Config | wall_ms | wire_bytes | batch_RTs | remote_embeds |
|--------|---------|------------|-----------|---------------|
| inproc | 1.01 | 0 | 0 | 0 |
| chorus_loopback | 0.63 | 2568 | 1 | 0 |
| prismapi_loopback | 0.54 | 2568 | 1 | 0 |

10-branch Send → **1 batch frame** (not 10). Stub LLM; transport-only variance.

**Command:** `python benchmark/distributed_proof.py --out benchmark/results/distributed_proof`

---

## Docs updated

- `handoffs/handoffCORE_MVP.md` — P5/P6 marked absorbed → Improve-2
- `docs/ENGINE_DESIGN_v0.1.md` §2.4 — transport rows marked wired
- `docs/DESIGN_v0.3_PRISM_ENGINE.md` §3 — CHORUS + PrismAPI wired status

---

## Verification

```text
python -m pytest tests/ -q
# 271 passed, 1 skipped in ~60s
```

LangGraph grep gate on `chorusgraph/{core,checkpoint,compat,transport}`: **clean** (compat shim only).

**No commits** per Director standing rule.

---

## Blockers / deviations

| Item | Status |
|------|--------|
| `BoundaryTranslator` class | **Not in prismlib-plus** — used `PrismProjector` at boundary instead |
| `ProjectionConfig.input_dim` | **Not a parameter** — uses `tenant_id`, `target_dim` |
| Redis two-process test | Requires live Redis + `CHORUSGRAPH_REDIS_URL`; skips otherwise (never fakes) |
| Azure two-VM proof | Stretch goal not run — loopback only |

---

*Improve-2 return · spines wired, Send batch over transport, federation zero re-embed tested, ChorusStack thresholds centralized.*
