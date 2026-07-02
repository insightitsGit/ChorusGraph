# Finance Multi-Agent ChorusGraph — Correct Implementation (Container F)

**Audience:** Engineers wiring ChorusGraph into multi-hop agent pipelines.  
**Status:** Reference implementation (H14 fix, Jul 2026).  
**Companion:** [`BENCHMARK.md`](BENCHMARK.md), [`PRODUCT_QA_BENCHMARK.md`](PRODUCT_QA_BENCHMARK.md), [`handoffs/handoffEF_finance_multiagent.md`](../handoffs/handoffEF_finance_multiagent.md).

---

## Summary

Container **F** is the **reference pattern** for applying ChorusGraph (cache gate, embed-once,
envelopes, Cortex) to a **multi-agent finance pipeline**. Container **E** is the fair LangGraph
baseline on the same workload.

After H14 fixes, F matches the library contract used by Container **B** on cache hits:
~11 ms / 0 tokens on repeats vs E ~2.6 s / ~700+ tokens.

**Do not copy the pre-fix F graph** (linear 6-node path, write-only envelopes, per-task cache wipe).
Use the patterns in this document.

---

## What we changed (before → after)

| # | Problem (broken F) | Fix | File(s) |
|---|-------------------|-----|---------|
| **F1** | Linear graph always ran `researcher → tool` even on cache hit | **Conditional routing** after `cache_gate`: hit → `writer`, miss → `researcher` | `container_f/nodes.py` → `route_after_cache_f`, `build_finance_graph_f` |
| **F2** | `_envelope_update()` called `project_text()` on every hop (5+ embeds/turn) | Reuse `raw_embedding_384` from ingress; on cache-hit path use `project_from_raw` only (`skip_embed=True`) | `container_f/nodes.py` → `_envelope_update` |
| **F3** | `resolve_envelope_artifact()` existed but was never called | `envelope_handoff()` resolves `previous_artifact` when `runtime` + `envelope_id` provided | `container_f/artifacts.py` |
| **F4** | `session_tool_cache.clear()` every task wiped envelopes + seeded FX keys | **Removed** — session cache persists for seeding and envelope resolution | `container_f/runner.py` |
| **F5** | `cache_gate` set only `tool_result`; compare queries need two rates | `collect_cached_tool_results()` expands hit into `tool_results[]` from session cache | `container_f/cache_helpers.py`, `cache_gate_node` wrapper |
| **F6** | Writer on cache hit got envelope JSON blob | On cache hit, writer uses **plain tool context** like B: `"Tool data (authoritative): {...}"` | `container_f/nodes.py` → `_writer_user_prompt` |
| **+** | No visibility into hop decisions | Structured JSONL trace (`CHORUS_F_TRACE=1`) | `container_f/trace.py` |

### Results after fix (12 tasks, seed 42, band 40%)

| | E | F (fixed) |
|--|---|-----------|
| Overall latency | 4,038 ms | **1,387 ms** |
| Repeat latency | ~2,600 ms | **~11 ms** |
| Tokens in (repeats) | ~700+ | **0** |
| Cache hit rate | 0% | **42%** |
| Success | 42% | **67%** |

Run artifact: `benchmark/results/h14_finance_ef_rerun/`

---

## Correct graph topology

### Cache MISS (full pipeline)

```
START → vector_ingress → cache_gate → researcher → tool → writer → validator → END
```

### Cache HIT (fast path — same as Container B)

```
START → vector_ingress → cache_gate ──hit──→ writer → validator → END
```

**Implementation:** conditional edge on `cache_gate`, not a linear edge to `researcher`:

```python
graph.add_conditional_edges(
    "cache_gate",
    route_after_cache_f,
    {"writer": "writer", "researcher": "researcher"},
)
```

`route_after_cache_f` mirrors B's `route_after_cache` / `route_after_cache_pattern`:

```python
def route_after_cache_f(state) -> str:
    if state.get("cache_hit") and state.get("tool_result"):
        return "writer"
    return "researcher"
```

**Reference:** `benchmark/container_f/nodes.py`, `chorusgraph/examples/finance_agent/patterns_graph.py`.

---

## Wiring checklist (copy when building a new Chorus multi-agent graph)

Use this checklist for any domain (finance F is the template; healthcare D still needs it).

| Step | Library API | Container F |
|------|-------------|-------------|
| 1. Embed once per turn | `make_vector_ingress_handler(runtime)` | `vector_ingress` node → sets `raw_embedding_384`, `query_vector_64` |
| 2. Cache gate | `make_cache_gate_handler(runtime, coarse_threshold=…, verify_threshold=…)` | `cache_gate` node before expensive hops |
| 3. Route on hit | Custom router returning `"writer"` or first LLM hop | `route_after_cache_f` |
| 4. Seed after tool | `seed_fx_cache_from_tool_calls(runtime, message, tool_calls, extra_queries=…)` | In `tool_node` after `fetch_exchange_rate` |
| 5. Expand multi-tool hit | App-specific (F: `collect_cached_tool_results`) | After gate on hit, set `tool_results[]` |
| 6. Template writer | `try_template_draft(message=…, tool_result=…, tool_results=…)` | `writer_node` — 0 LLM when FX/compound data suffices |
| 7. Plain writer on hit | Same as B — authoritative tool payload in prompt | `_writer_user_prompt` when `cache_hit` |
| 8. Envelope write | `project_text(cache, json, raw_384=raw_from_state(state))` | `_envelope_update` — **reuse raw**, don't re-embed message |
| 9. Envelope read | `resolve_envelope_artifact(runtime, envelope_id)` | Inside `envelope_handoff(..., runtime=runtime)` |
| 10. Session cache | Do **not** clear `session_tool_cache` per turn | `ContainerFRunner` — PrismCache + session keys persist |
| 11. Cortex (optional) | `runtime.cortex.recall_structured(message, cache=…, raw_384=…)` | Memory tasks only |
| 12. Trace (dev) | `benchmark/container_f/trace.py` | JSONL at `benchmark/results/f_trace/container_f_trace.jsonl` |

---

## Code patterns (the right way)

### 1. Cache gate wrapper with multi-tool recovery (F5)

The library gate returns one `tool_result`. Wrap it:

```python
update = dict(cache_gate_base(state))
if update.get("cache_hit") and update.get("tool_result"):
    tool_results = collect_cached_tool_results(runtime, message, update["tool_result"])
    update["tool_results"] = tool_results
```

See `benchmark/container_f/cache_helpers.py`.

### 2. Embed-once + envelope projection (F2)

```python
raw_arr = raw_from_state(state)
if skip_embed and raw_arr is not None:
    _, envelope = project_from_raw(runtime.cache, raw_arr)  # cache-hit fast path
else:
    _, envelope = project_text(runtime.cache, compact_json(artifact), raw_384=raw_arr)
```

Never call `project_text(cache, text)` without `raw_384` when ingress already ran.

### 3. Envelope handoff with read (F3)

```python
def envelope_handoff(*, hop, envelope_id, hop_input=None, runtime=None, ...):
    payload = {"hop": hop, "previous_envelope_id": envelope_id}
    if runtime and envelope_id:
        resolved = resolve_envelope_artifact(runtime, envelope_id)
        if resolved:
            payload["previous_artifact"] = resolved
    if hop_input:
        payload["hop_input"] = hop_input
    return compact_json(payload)
```

Downstream LLM hops get **pointer + resolved artifact + hop-local input** — not a growing transcript.

### 4. Writer prompt on cache hit (F6)

Match Container B — not envelope JSON:

```python
if state.get("cache_hit"):
    parts = [f"User question: {message}"]
    if tool_results:
        parts.append(f"Tool observations (authoritative): {tool_results}")
    elif tool_result:
        parts.append(f"Tool data (authoritative): {tool_result}")
    user = "\n".join(parts)
else:
    user = envelope_handoff(hop="writer", envelope_id=..., runtime=runtime, ...)
```

Template path (`try_template_draft`) should run **before** LLM on both hit and miss when tool data is sufficient.

### 5. Session cache persistence (F4)

```python
# WRONG — do not do this in runner.run():
runtime.session_tool_cache.clear()

# RIGHT — let session_tool_cache accumulate:
#   - query string → tool_result (from seed_tool_cache)
#   - env:{envelope_id} → hop artifact
```

Clear only on new session / tenant if required — not every task.

---

## Trace logging (debugging)

Enable structured hop trace:

```powershell
$env:CHORUS_F_TRACE = "1"
$env:CHORUS_F_TRACE_PATH = "benchmark/results/f_trace/container_f_trace.jsonl"
python -m benchmark.run_finance_multiagent --tasks 12 --container F --band 40
```

**Events to inspect:**

| Event | Meaning |
|-------|---------|
| `route_after_cache` | `route=writer` on hit — F1 working |
| `cache_gate_result` | `cache_hit`, `tool_results_count` — F5 working |
| `envelope_write` | `embed_mode=reuse_ingress` on hit — F2 working |
| `envelope_handoff` | `resolved=true` — F3 working |
| `writer_prompt` | `mode=cache_hit_plain` on hit — F6 working |
| `task_end` | `hops` list — should be 4 nodes on hit, 6 on miss |

**Expected cache-hit trace:**

```
vector_ingress → cache_gate → writer → validator
latency ~11ms, tokens 0, embed_count 2
```

---

## File map

```
benchmark/container_f/
  nodes.py           # Graph build, route_after_cache_f, hop nodes
  artifacts.py       # envelope_handoff, resolve, store
  cache_helpers.py   # collect_cached_tool_results (F5)
  trace.py           # JSONL trace
  runner.py          # ContainerFRunner (no session cache clear)

benchmark/container_e/
  runner.py          # LangGraph baseline (no Chorus)

benchmark/finance_multiagent_shared.py  # Shared state, validate_draft, heuristic_tool_plan
benchmark/run_finance_multiagent.py     # E vs F harness

chorusgraph/examples/finance_agent/
  patterns_graph.py  # Container B reference (single-agent)
  nodes.py           # make_cache_gate_handler, seed_fx_cache_from_tool_calls
```

---

## How to run and verify

```powershell
# Offline (routing + cache-hit path structure)
python -m pytest tests/test_finance_multiagent.py -q

# Live E vs F
$env:GEMINI_API_KEY = (Get-Content .env | Where-Object { $_ -match '^GEMINI_API_KEY_default=' } | ForEach-Object { $_.Split('=',2)[1].Trim() })
python -m benchmark.run_finance_multiagent --tasks 12 --seed 42 --band 40 --container both --output-dir benchmark/results/h14_finance_ef_rerun
```

**Acceptance signals:**

- F repeat latency **< 50 ms** (target ~11 ms, comparable to B ~8 ms)
- F repeat **tokens_in = 0**
- Trace shows `route=writer` and 4 hops on cache hit
- E repeats still pay full LLM cost (no cache — expected)

---

## Applying this pattern elsewhere (e.g. healthcare D)

Use the same checklist. Healthcare D still needs:

- `cache_gate` at ingress
- Conditional routing on hit
- Cache seeding after retrieve/tool hops
- Envelope read in handoffs
- No per-task `session_tool_cache.clear()`

See [`PRODUCT_QA_BENCHMARK.md`](PRODUCT_QA_BENCHMARK.md) § Container D backlog.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-07-02 | H14 F1–F6 fixes; trace logging; E vs F rerun documented |

*Container F · reference Chorus multi-agent wiring · mirror B on cache hit · envelopes read+write.*
