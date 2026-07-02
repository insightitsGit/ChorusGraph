# Product Q&A — Benchmark Containers vs ChorusGraph Library

**Audience:** Directors, buyers, engineers auditing benchmark claims.  
**Status:** Living document (H14, Jul 2026). **Container F fixes applied** — see [`FINANCE_MULTIAGENT_CHORUS.md`](FINANCE_MULTIAGENT_CHORUS.md).  
**Companion:** [`BENCHMARK.md`](BENCHMARK.md), [`DESIGN_v0.2.md`](DESIGN_v0.2.md) §8, [`BENCHMARK_RESULTS.md`](BENCHMARK_RESULTS.md).

---

## Executive summary

The **ChorusGraph library is implemented correctly** for its core value proposition: semantic cache,
embed-once ingress, template fast path, and conditional skip of expensive nodes. That story is
**proven in Container B** (finance single-agent) and **Container F** (finance multi-agent, after
H14 fixes).

Earlier benchmark integrations had wiring mistakes under `benchmark/container_*` — not library
bugs. **Container F is now the reference multi-agent pattern**; healthcare D still needs the same
wiring.

| Container | Domain | Shape | Chorus wired correctly? | Thesis demonstrable? |
|-----------|--------|-------|---------------------------|----------------------|
| **A** | Finance | Single-agent LangGraph | N/A (baseline) | — |
| **B** | Finance | Single-agent Chorus | **Yes** | **Yes** (cache + speed) |
| **C** | Healthcare | Multi-agent LangGraph | N/A (baseline) | — |
| **D** | Healthcare | Multi-agent Chorus | **No** (no cache_gate, write-only envelopes) | **No** |
| **E** | Finance | Multi-agent LangGraph | N/A (baseline) | — |
| **F** | Finance | Multi-agent Chorus | **Yes** (F1–F6 fixed Jul 2026) | **Yes** (cache + speed vs E) |

**H14 rerun (12 tasks, seed 42, 40% band, post-fix):** E ~4.0s / 0% cache; F ~1.4s / **42% cache
hit** / **~11 ms on repeats** (comparable to B ~8 ms).

---

## Q&A — For product and buyer conversations

### Q1: Does ChorusGraph work?

**A:** Yes, when integrated the way Container B does. On finance repeats, B achieves ~8 ms p50, 0
LLM tokens, ~42% cache hit rate at 40% repeat band. The library’s `cache_gate`, `vector_ingress`,
`seed_fx_cache_from_tool_calls`, and `try_template_draft` are functional.

**Evidence:** `benchmark/results/h14_all_containers/`, production path in
`chorusgraph/examples/finance_agent/patterns_graph.py`.

---

### Q2: Why did Container F feel slow on cache hits before the fix?

**A (historical):** Pre-fix F used a **linear 6-node graph** without B's **conditional routing**.
On cache hit it still ran researcher + tool and re-embedded every hop (~34 ms vs B ~8 ms).

**A (current):** Fixed in H14 (F1–F6). F now routes `cache_gate → writer` on hit (~11 ms, 0
tokens). See [`FINANCE_MULTIAGENT_CHORUS.md`](FINANCE_MULTIAGENT_CHORUS.md).

**Reference:** `benchmark/container_f/nodes.py` → `route_after_cache_f`; compare
`chorusgraph/examples/finance_agent/patterns_graph.py`.

---

### Q3: What is the “envelope / vector substrate” story? Does F prove it?

**A:** DESIGN intent: hops pass **envelope pointers**; downstream resolves artifacts from the store
instead of growing text transcripts.

**Container F (post-fix):**

- `store_envelope_artifact()` writes artifacts keyed by `envelope_id`.
- `envelope_handoff(..., runtime=runtime)` calls **`resolve_envelope_artifact()`** and includes
  `previous_artifact` in the LLM payload when present.
- `_envelope_update()` reuses **`raw_embedding_384`** from ingress (embed-once).
- LangGraph state still carries `tool_result` / `tool_plan` for scoring — envelopes augment, not
  replace, state on the finance path.

**Healthcare D** still lacks cache_gate and full read path — use F as the template.

**Code:** `benchmark/container_f/artifacts.py`, `benchmark/container_f/nodes.py`.

---

### Q4: Why does healthcare (C vs D) show 0% cache hits?

**A:** **`cache_gate` was never wired** into healthcare D. H13 scoped C/D to test envelope
handoffs, not cache. D uses `FinanceRuntime` / `PrismCache` only for **embedding** hop artifacts,
not for semantic skip.

- **C** — intentionally no cache (fair LangGraph baseline).
- **D** — no `make_cache_gate_handler()`, no seeding after `retrieve_guidelines`, no template skip.
- Repeat variants were added to `healthcare_workload.py` but nothing consumes them for LLM skip.

**This is optional by omission in the benchmark rig**, not proof that healthcare can’t use cache.

**Code:** `benchmark/container_d/` (no cache_gate node); compare `benchmark/container_f/nodes.py`
and `chorusgraph/examples/finance_agent/nodes.py`.

---

### Q5: Is `cache_gate` optional in the product?

**A:** **Yes.** It is a **built-in node** you wire per graph when a workload has cacheable,
`REPLAY_SAFE` sections (e.g. FX rates). It is not automatic. Requires:

1. `vector_ingress` (embed once per turn).
2. `cache_gate` before expensive children.
3. **Conditional routing** on hit (skip retrieve / react / tool).
4. **Cache seeding** after first tool result (`seed_fx_cache_from_tool_calls` or equivalent).
5. **Template or cheap writer** on hit (`try_template_draft`).

Finance **B and F** implement (1)–(5). Healthcare D has none of (1)–(5).

---

### Q6: Can we compare B’s 8 ms to healthcare D’s latency?

**A:** **No.** Different domains, different graphs, different cache wiring. Fair pairs only:

- **A vs B** (finance single-agent)
- **C vs D** (healthcare multi-agent)
- **E vs F** (finance multi-agent)

Cross-pair comparisons are illustrative at best, misleading for thesis claims.

---

### Q7: Why is F’s task success rate sometimes lower than B on small runs?

**A:** Early H14 (pre-fix) F ~58% vs B ~83%. After F fixes, E vs F rerun: **F 67% vs E 42%**.
Remaining gap vs B is mostly **graph shape** (4-hop researcher JSON vs ReAct `AgentNode`) and
small-n variance. Scale to 60+ tasks before success-rate claims.

---

### Q8: Does the library say “embed once per turn”? Does F follow that?

**A:** Yes (post-fix). One ONNX embed at `vector_ingress`; `raw_embedding_384` shared via
`raw_from_state(state)` in cache_gate and `_envelope_update`. On cache-hit path, envelopes use
`project_from_raw` only (`embed_mode=reuse_ingress` in trace).

---

### Q9: What did `session_tool_cache.clear()` do? (historical)

**A:** Pre-fix F cleared `session_tool_cache` every task — **removed in F4**. Session cache now
persists FX seeds and envelope artifacts for the session. PrismCache also persists on
`FinanceRuntime`.

---

### Q10: What should we tell a buyer about multi-agent ChorusGraph today?

**A (updated Jul 2026):**

- **Proven:** Semantic cache + fast path in finance single-agent (**B**) and multi-agent (**F**).
  F repeats: ~11 ms, 0 tokens, ~42% hit rate at 40% band (same workload as A/B).
- **Fair baseline:** E vs F on identical finance workload — E ~4s, F ~1.4s overall; repeats E ~2.6s
  vs F ~11 ms.
- **Not yet:** Healthcare cache/envelope story (**D** — apply F pattern).
- **Reference implementation:** [`FINANCE_MULTIAGENT_CHORUS.md`](FINANCE_MULTIAGENT_CHORUS.md).

---

## Library contract vs benchmark mistakes

### How Container B (correct) uses the library

```
START → vector_ingress → cache_gate ─┬─ hit  → writer → validator → END
                                     ├─ compound → compound_tool → writer → …
                                     └─ miss → react_agent → writer → …
```

| Mechanism | Library location | B behavior |
|-----------|------------------|------------|
| Embed once | `make_vector_ingress_handler` | ✓ Per turn |
| Cache gate | `make_cache_gate_handler` + `gate()` | ✓ Two-stage recall + verify |
| Skip on hit | `route_after_cache_pattern` | ✓ Jump to writer |
| Seed cache | `seed_fx_cache_from_tool_calls` | ✓ After FX tool |
| Fast writer | `try_template_draft` | ✓ 0 LLM on simple FX hit |
| Cortex | `FinanceRuntime.cortex` | ✓ Memory tasks |

**Reference:** `chorusgraph/examples/finance_agent/patterns_graph.py`,
`chorusgraph/examples/finance_agent/nodes.py`.

---

### How Container F (correct — post H14 fix)

```
START → vector_ingress → cache_gate ─┬─ hit  → writer → validator → END
                                     └─ miss → researcher → tool → writer → validator → END
```

| Mechanism | Library location | F behavior |
|-----------|------------------|------------|
| Embed once | `make_vector_ingress_handler` | ✓ Per turn; reused in gate + envelopes |
| Cache gate | `make_cache_gate_handler` + `gate()` | ✓ Two-stage recall + verify |
| Skip on hit | `route_after_cache_f` | ✓ Jump to writer |
| Multi-tool hit | `collect_cached_tool_results` | ✓ `tool_results[]` on compare queries |
| Seed cache | `seed_fx_cache_from_tool_calls` | ✓ After FX tool |
| Fast writer | `try_template_draft` + plain prompt on hit | ✓ 0 LLM on simple FX hit |
| Envelope read | `resolve_envelope_artifact` in `envelope_handoff` | ✓ `previous_artifact` in payload |
| Session cache | No per-task clear | ✓ Persists seeds + envelopes |
| Trace | `container_f/trace.py` | ✓ JSONL hop events |

**Reference:** [`FINANCE_MULTIAGENT_CHORUS.md`](FINANCE_MULTIAGENT_CHORUS.md),
`benchmark/container_f/nodes.py`.

---

### How Container F (broken — pre H14 fix) diverged

| Mechanism | Expected | Pre-fix F | Impact |
|-----------|----------|-----------|--------|
| Skip on hit | Conditional edge to writer | Linear 6-node path always | ~34 ms repeats |
| Embed once | Reuse `raw_384` | Re-embed per hop | CPU tax |
| Envelope read | `resolve_envelope_artifact` | Never called | Write-only |
| Multi-tool cache | `tool_results` on hit | Only `tool_result` | Compare queries fail |
| Session cache | Persist | `clear()` per task | Lost envelopes |

**Do not revert to this pattern.**

---

### How Container D (healthcare) diverges

| Mechanism | Finance B | Healthcare D |
|-----------|-----------|--------------|
| `cache_gate` | ✓ | ✗ Not in graph |
| Cache seeding | ✓ After FX tool | ✗ Retrieve is keyword lookup, not seeded |
| Skip LLM on repeat | ✓ | ✗ No repeat consumption |
| `enable_cortex` | ✓ (memory tasks) | ✗ `enable_cortex=False` |
| Envelope read | N/A in B | ✗ Write-only (same as F) |

**Reference:** `benchmark/container_d/nodes.py`, `handoffs/handoffbackH13.md`.

---

## Documented findings checklist (engineering backlog)

Use this as the single source for “what’s wrong with the benchmark integrations.”

### Container F (finance multi-agent) — DONE (Jul 2026)

- [x] **F1** Conditional routing after `cache_gate` → `writer` on hit
- [x] **F2** Reuse ingress vectors in `_envelope_update`; `skip_embed` on cache path
- [x] **F3** `resolve_envelope_artifact()` wired in `envelope_handoff`
- [x] **F4** Removed `session_tool_cache.clear()` per task
- [x] **F5** `collect_cached_tool_results` for multi-FX compare on hit
- [x] **F6** Plain tool writer prompt on cache hit (like B)
- [x] **F7** JSONL trace logging (`CHORUS_F_TRACE`)

Documented in [`FINANCE_MULTIAGENT_CHORUS.md`](FINANCE_MULTIAGENT_CHORUS.md).

### Container D (healthcare multi-agent) — P1

- [ ] **D1** Wire `cache_gate` at ingress (or document healthcare as clinical/safety domain, not
      speed domain).
- [ ] **D2** Define cacheable artifacts + `category_slug` for retrieve summaries.
- [ ] **D3** Seed PrismCache after first retrieve hop.
- [ ] **D4** Wire envelope read path (same as F3).
- [ ] **D5** Add `cache_hit` to `MultiAgentMeasurement` schema.

### Cross-cutting — P2

- [ ] **X1** Scale runs (60+ tasks) before success-rate claims.
- [ ] **X2** Update `BENCHMARK_RESULTS.md` after F/D fixes.
- [ ] **X3** Do not apply hop-level `_cached_llm` / `get_or_call` hacks (optimization theater, not
      thesis fix).

---

## Fair comparison matrix (what is actually the same)

| Shared across finance A/B/E/F | Different by design |
|------------------------------|---------------------|
| `benchmark/workload.py` | Graph topology (ReAct vs 4-hop) |
| `default_finance_registry()` tools | Cache / Cortex (A,E none; B,F yes) |
| `score_task_success` / rubric | Handoff model (scratchpad / context / envelope) |
| `InstrumentedGeminiClient` | Prompts (REACT vs RESEARCHER JSON) |
| Repeat bands 20/40/60% | Measurement fields (`hop_metrics` on E/F only) |

---

## Key code paths (quick navigation)

| Topic | Path |
|-------|------|
| **Correct cache routing (B)** | `chorusgraph/examples/finance_agent/patterns_graph.py` |
| **cache_gate implementation** | `chorusgraph/examples/finance_agent/nodes.py` → `make_cache_gate_handler` |
| **Cache gate algorithm** | `chorusgraph/cache_gate/gate.py` |
| **Template fast path** | `chorusgraph/transforms/templates.py` → `try_template_draft` |
| **Correct multi-agent Chorus (F)** | [`FINANCE_MULTIAGENT_CHORUS.md`](FINANCE_MULTIAGENT_CHORUS.md) |
| **F graph (reference)** | `benchmark/container_f/nodes.py` |
| **F trace log** | `benchmark/results/f_trace/container_f_trace.jsonl` |
| **E vs F rerun results** | `benchmark/results/h14_finance_ef_rerun/` |
| **D healthcare (no cache)** | `benchmark/container_d/nodes.py` |
| **H14 unified results** | `benchmark/results/h14_all_containers/REPORT.md` |
| **H13 return / root causes** | `handoffs/handoffbackH13.md` |
| **E/F design intent** | `handoffs/handoffEF_finance_multiagent.md` |

---

## Commands (reproduce H14)

```powershell
$env:GEMINI_API_KEY = (Get-Content .env | Where-Object { $_ -match '^GEMINI_API_KEY_default=' } | ForEach-Object { $_.Split('=',2)[1].Trim() })
python -m benchmark.run_all_benchmarks --tasks 12 --seed 42 --band 40 --output-dir benchmark/results/h14_all_containers
```

```powershell
python -m pytest tests/test_finance_multiagent.py tests/test_container_d_artifacts.py -q
```

---

## Revision history

| Date | Change |
|------|--------|
| 2026-07-02 | Initial Q&A: F integration gaps, D missing cache_gate |
| 2026-07-02 | F1–F7 fixes applied; F marked correct; link `FINANCE_MULTIAGENT_CHORUS.md` |

*Product Q&A · library proven in B + F · D still needs F pattern · see FINANCE_MULTIAGENT_CHORUS.md.*
