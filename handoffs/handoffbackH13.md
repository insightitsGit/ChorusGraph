# Handoff H13 — Return · Engineer → Director (Amin)

**Date:** 2026-07-02 (updated end-of-session)  
**Status:** Part A largely complete · **Part B rig built but thesis NOT proven** — D implementation was wrong; partial fixes landed; **results still do not show D beating C as depth grows.**  
**Successor must read §8–§10 before running more benchmarks.**

---

## 1. Executive summary (honest)

| Part | Deliverable | Status |
|------|-------------|--------|
| **A1** Cortex native 128-d from `raw_384` | `chorusgraph/transforms/cortex_projector.py` | ✅ Shipped + tests |
| **A2** 300-task volume bands 20/40/60 | `benchmark/results/h12_volume_300` | ⚠️ **900 tasks completed**; bands 20/40 usable; **band 60 quota-blocked** (0 valid A rows) |
| **A3** Release tag | `v0.9.1` / `v0.10.0` | ⏸ Awaiting Director |
| **B** Multi-agent C vs D rig | `container_c/`, `container_d/`, `run_multiagent.py` | ✅ Built |
| **B** Fair baseline audit | `container_c/FAIR_BASELINE_C.md` | ✅ Updated (prompt parity corrected) |
| **B** Vector-substrate thesis | D flatter tokens/latency vs C as depth → 6 | ❌ **NOT demonstrated** |

**Bottom line for Director:** Single-agent finance (Container B) shows dramatic wins via **semantic cache + template writer** (~13 ms p50 at 40% repeat band). Multi-agent healthcare (Container D) was supposed to show **bounded envelope handoffs** beating LangGraph's growing transcript. Early D was **instrumentation-only** (vectors written, never read). Several bugs were fixed, but **D is still slower than C at depth 6** on the latest run, and the primary chart (tokens vs depth) does not yet show D diverging favorably.

**This is not the result we need.** The next engineer must implement the missing **read path** (envelope resolution + optional cache skip), not run more benchmarks on the current D.

---

## 2. Why the numbers look wrong (read this first)

### 2.1 Single-agent B ≠ multi-agent D

| | Finance A/B (H12 volume) | Healthcare C/D (H13) |
|--|--------------------------|----------------------|
| **What it tests** | One ReAct agent + cache gate | 2–6 agent linear pipeline |
| **B fast path** | Cache hit → **0 LLM calls**, ~**13 ms** p50 (band 40%) | **No cache** in C or D |
| **Why B wins** | Skips Gemini entirely on repeat queries | Every case calls Gemini 2–6× |
| **Vector role** | Embed once → cache_gate → skip tool + LLM | Was: embed per hop, **unused** |

**Do not compare** H12 B latency (13 ms) to H13 D latency (~17 s). Different domains, different fast paths. The finance win comes from **cache + template writer**, not from ONNX alone.

### 2.2 What H13 thesis actually requires (from `handoffH13.md` B2)

> **Falsifiable thesis:** D should stay **flatter** as pipeline depth grows (vector hops ~constant, no re-reading growing transcript); C **grows** (each agent re-reads history). **If D doesn't diverge from C as depth increases, the thesis fails.**

**Current data (latest fixed run, §6):**

| Depth | C tokens_in | D tokens_in | C latency | D latency |
|-------|-------------|-------------|-----------|-----------|
| 2 | 107 | 242 | 5.4 s | 6.8 s |
| 4 | 998 | **755** | 12.5 s | 14.2 s |
| 6 | 837* | 1133 | 13.2 s* | 17.4 s |

\*Depth-6 C skewed: **75% abstain rate** → writer LLM often skipped (cheaper path).

D shows **token savings at depth 4 only**. At depth 6, D has **more** tokens and **more** latency. **Thesis not proven.**

### 2.3 Gemini is the bottleneck, not Prism

Per-hop profiling (all D runs): `vector_ingress` / envelope embed ≈ **3–11 ms** total per case. Analyze/safety/writer hops ≈ **2–7 s** each. **JSON mode, prompt shape, and API variance** dominate; ONNX is negligible.

---

## 3. Part A — Cortex 128-d + volume

### A1 — Cortex fix ✅

**Finding:** H12 passed shared **64-d** cache vector into Cortex recall; native Cortex projection is **128-d**.

**Fix:** `project_cortex_from_raw()` in `chorusgraph/transforms/cortex_projector.py`; wired in `cortex_service.py`, `structured_recall.py`.

```powershell
python -m pytest tests/test_cortex_projector.py -q   # 3 passed
```

### A2 — Volume run ⚠️

**Path:** `benchmark/results/h12_volume_300/`

| Band | Tasks | Valid paired | Notes |
|------|-------|--------------|-------|
| 20% | 300×2 | ~287 A/B | Usable |
| 40% | 300×2 | ~287 A/B | B p50 **13 ms** (cache hits); strong story |
| 60% | 300×2 | **0 A**, 70 B | `quota_blocked: true` — primary key exhausted |

**Headline (bands 20/40):** B cheaper, faster on repeats, higher accuracy. Band 60 incomplete.

**Fixes during run:**
- `chorusgraph/memory/cortex_compat.py` — prismcortex `notes: null` validation
- `chorusgraph/memory/async_digest.py` — digest failures don't kill run
- `benchmark/analyze.py` — `format_ci_table()` handles missing metrics
- Rebuilt via `python -m benchmark.rebuild_analysis benchmark/results/h12_volume_300 20,40,60 --tasks 300 --seed 42`

**API keys:** Primary `GEMINI_API_KEY` in `.env` hit 10k/day limit. Use `GEMINI_API_KEY_default` for live runs:

```powershell
$env:GEMINI_API_KEY = (Get-Content .env | Where-Object { $_ -match '^GEMINI_API_KEY_default=' } | ForEach-Object { $_.Split('=',2)[1].Trim() })
```

---

## 4. Part B — Multi-agent timeline (what happened)

### 4.1 What was built (correct)

```
benchmark/
  healthcare/
    abstain.py           # shared C/D abstain gate (added later)
    kb.py, tools.py, prompts.py
  healthcare_workload.py   # 8 cases × depth 2/4/6
  multiagent_measure.py    # HopMetric, embed_count
  run_multiagent.py
  container_c/runner.py    # LangGraph baseline — growing text state
  container_d/
    artifacts.py           # envelope handoffs, compact artifacts
    nodes.py               # role-typed D hops
    prompts.py             # JSON-shaped prompts (NOT same as C)
    runtime.py             # enable_cortex=False lightweight runtime
    runner.py
tests/
  test_multiagent_pipeline.py
  test_container_d_artifacts.py
  test_healthcare_envelope_runtime.py
  test_cortex_compat.py
```

**Pipeline (both C and D):**

| Depth | Agents |
|-------|--------|
| 2 | intake → writer |
| 4 | intake → retrieve → analyze → writer |
| 6 | intake → retrieve → analyze → drug_check → safety → writer |

### 4.2 Run history

| Run dir | Cases | D state | Notes |
|---------|-------|---------|-------|
| `h13_multiagent_dryrun` | 12 | **Broken** | D wrapped C nodes; vectors write-only |
| `h13_multiagent_envelope_fix` | 12 | Envelope nodes | D **21.3 s** vs C **14.8 s** at depth 6 |
| `h13_multiagent_optimized` | 12 | compact_json + no Cortex | **429 quota** on primary key |
| `h13_multiagent_optimized` (retry) | 12 | same | With default key; still slow |
| **`h13_multiagent_fixed`** | 12 | **Current best** | Envelope-native handoffs, analyze bug fixed, no orphan ingress |

### 4.3 Bugs found in Container D (root cause of bad results)

#### Bug 1 — Vectors were write-only (CRITICAL)

- Every hop called `project_text()` → stored `envelope_id` + `prism_sequence`
- Next hops only echoed `previous_envelope_id` as a **string in JSON prompt**
- **No cache lookup, no envelope hydration, no vector similarity**
- Envelopes were telemetry, not communication

#### Bug 2 — `compact_upstream` dropped retrieve at analyze (CRITICAL)

```python
# WRONG (removed): compact_upstream("analyze", retrieve_artifact) called compact_intake()
# → analyze hop got EMPTY upstream; retrieve summary missing
```

Caused 5–7 s analyze hops and wrong/abstain behavior.

#### Bug 3 — Orphan `vector_ingress`

- Embedded case presentation once per case
- **No agent hop read** `query_vector_64` or `raw_embedding_384`
- Pure overhead (~5 ms + graph complexity)

**Fixed:** Removed from D graph in `h13_multiagent_fixed` build.

#### Bug 4 — Unfair API mode

- D used `generate_json()` (JSON MIME, max 2048 out, temp 0.0) on 5 hops
- C used `generate()` (max 1024, temp 0.2)

**Fixed:** D structured hops now use `generate()` + `parse_json_object()`.

#### Bug 5 — False parity documentation

- `FAIR_BASELINE_C.md` claimed shared `healthcare/prompts.py`
- D uses `container_d/prompts.py` (JSON-shaped outputs)

**Fixed:** Doc updated.

#### Bug 6 — Abstain asymmetry

- C: text safety → `"ABSTAIN" in verdict`
- D: structured `should_abstain()` + evidence gates

**Fixed:** Shared `benchmark/healthcare/abstain.py` for both. **Still asymmetric outcomes** on small n (C 75% abstain vs D 25% at depth 6 in latest run) due to different safety prompts and LLM variance.

#### Bug 7 — Growing transcript in C not matched by constant envelope in D

- C at depth 6: `analysis` string **grows** each hop (`+=` append)
- D: bounded `hop_input` per hop (correct intent)
- **But D never skips LLM** via cache — so token savings are modest and latency still Gemini-bound

---

## 5. Fixes landed (current code state)

| Fix | File(s) | What |
|-----|---------|------|
| Envelope-native handoffs | `artifacts.py` | `envelope_handoff()` — no `upstream` blob; only `previous_envelope_id` + `hop_input` |
| Artifact store | `artifacts.py`, `nodes.py` | `store_envelope_artifact()` keyed by `envelope_id` in `session_tool_cache` |
| Analyze handoff | `nodes.py` | `hop_input` includes **both** `intake` and `retrieve` compact artifacts |
| `compact_artifact(source_hop)` | `artifacts.py` | Compacts by **producer** hop, not consumer |
| Lightweight runtime | `runtime.py`, `FinanceRuntime.enable_cortex` | No ~450 ms Cortex cold start |
| Text-mode structured LLM | `nodes.py` | `_structured()` = `generate()` + parse (same API as C) |
| Removed orphan ingress | `runner.py` | START → first agent (no unused embed) |
| Shared abstain | `healthcare/abstain.py` | C and D use same evidence gates |
| Embed count | `multiagent_measure.py` | `embed_count = len(prism_sequence)` |
| Cortex digest tolerance | `cortex_compat.py`, `async_digest.py` | Volume run survives 429 digest errors |
| analyze.py CI table | `analyze.py` | Missing metrics don't crash aggregate rebuild |

**Tests (offline, no API):**

```powershell
python -m pytest tests/test_container_d_artifacts.py tests/test_healthcare_envelope_runtime.py tests/test_multiagent_pipeline.py tests/test_cortex_compat.py tests/test_cortex_projector.py -q
# 20 passed (as of this handoff)
```

---

## 6. Latest benchmark results (`h13_multiagent_fixed`)

**Run:** 12 cases, seed 42, `GEMINI_API_KEY_default`, both C and D.

```powershell
$env:GEMINI_API_KEY = (Get-Content .env | Where-Object { $_ -match '^GEMINI_API_KEY_default=' } | ForEach-Object { $_.Split('=',2)[1].Trim() })
python -m benchmark.run_multiagent --cases 12 --output-dir benchmark/results/h13_multiagent_fixed
```

### Aggregate

| Container | Depth | Latency | tokens_in | tokens_out | Abstain | Success | D embeds |
|-----------|-------|---------|-----------|------------|---------|---------|----------|
| C | 2 | 5.4 s | 107 | 119 | 0% | 50% | — |
| C | 4 | 12.5 s | 998 | 384 | 0% | 75% | — |
| C | 6 | 13.2 s | 837 | 305 | **75%** | 50% | — |
| D | 2 | 6.8 s | 242 | 141 | 0% | 50% | 1 |
| D | 4 | 14.2 s | **755** | 361 | 0% | 50% | 3 |
| D | 6 | 17.4 s | 1133 | 394 | 25% | 50% | 5 |

### Per-hop (depth 6 averages)

| Hop | C latency | C tokens_in | D latency | D tokens_in |
|-----|-----------|-------------|-----------|-------------|
| intake | 1.7 s | 54 | 2.1 s | 55 |
| retrieve | 2.6 s | 208 | 3.4 s | 274 |
| analyze | 3.4 s | 274 | **4.5 s** | **204** |
| drug_check | 0.8 s | 55 | 1.3 s | 127 |
| safety | 3.9 s | 192 | 4.0 s | 306 |
| writer | 0.8 s* | 55* | 2.1 s | 167 |

\*C writer often skipped on abstain (0 ms, 0 tokens).

### Interpretation

- **D analyze tokens lower than C** (204 vs 274) — bounded handoff working at that hop
- **D still slower** — Gemini wall time, not embeds; JSON-shaped prompts; more writer runs (lower abstain)
- **Depth 4 token win for D** (755 vs 998) — directionally correct for thesis
- **Depth 6 fails thesis** — D tokens and latency both worse than C
- **n=4 per depth** — too small for conclusions; high variance (case-003 intake spike 13 s on D)

**Verdict: Thesis not proven. Do not claim D wins.**

---

## 7. Architecture — what C vs D actually do today

### Container C (baseline)

```
START → intake → retrieve → analyze → drug_check → safety → writer → END
```

- **State:** Growing text (`intake_summary`, `analysis` appended each hop, full `retrieved` docs in prompts)
- **LLM:** `generate()` all hops
- **Tools:** `retrieve_guidelines`, `check_drug_interactions` called in code
- **No vectors, no cache, no Cortex**

### Container D (current)

```
START → intake → retrieve → analyze → drug_check → safety → writer → END
```

- **State:** `hop_artifacts` dict + `latest_envelope_id` + `prism_sequence`
- **Handoff:** `envelope_handoff(hop, envelope_id, hop_input)` — compact JSON per hop
- **Envelope:** `project_text(compact_json(artifact))` per hop; stored in `session_tool_cache["env:{id}"]`
- **LLM:** `generate()` + JSON parse for structured hops; plain `generate()` for writer
- **Runtime:** `enable_cortex=False` (cache + projector only)
- **Missing:** No `cache_gate`, no envelope **read** on next hop, no LLM skip

### Container B (finance — why single-agent looks "much faster")

```
START → vector_ingress → cache_gate → [react_agent | writer template] → validator → END
```

On cache hit: **skip tool + skip LLM** → ~13 ms. **This is what D healthcare needs analogously** — not just envelope writes.

---

## 8. What must be built to get the result we need

The successor should **not** run another 12-case dry-run until these are implemented:

### 8.1 Envelope read path (P0)

**Today:** `store_envelope_artifact(runtime, envelope_id, artifact)` writes; nothing reads except tests.

**Required:**
1. Next hop calls `resolve_envelope_artifact(runtime, previous_envelope_id)` when `hop_input` is insufficient
2. Or: hops pass **only** `envelope_id` + hop-local tool output; model prompt says "prior context at envelope X" and runtime injects compact resolved artifact server-side (not duplicate JSON in prompt)

### 8.2 Healthcare cache gate (P0 — the B analog)

Wire finance `cache_gate` pattern into healthcare D:

1. After each hop, envelope vector registered in cache with artifact payload
2. Next hop: coarse + verify lookup on incoming context
3. On hit: **skip LLM**, hydrate artifact from cache, proceed

Without this, D will never show the dramatic speedups seen in finance B.

### 8.3 Depth-scaled workload (P1)

- Run **≥60 cases** (10 per depth × 2 containers) on paid key
- Report **paired** per-case delta at depth 2, 4, 6
- Primary chart: `tokens_in` vs `pipeline_depth` with error bars
- **Exclude abstain-skipped cases** from latency comparison OR report separately

### 8.4 Fair comparison options (P1)

Pick one and document:

| Option | C | D |
|--------|---|---|
| **A — Same prompts** | Switch C to JSON or D to `healthcare/prompts.py` | |
| **B — Same API** | ✅ Already done (generate + parse) | |
| **C — Same abstain** | Tune safety prompts so abstain rates match on safety cases | |

### 8.5 Optional Cortex for healthcare (P2)

`handoffH13.md` says D includes Cortex. Current D sets `enable_cortex=False`. Re-enable only if recall path is wired and measured — otherwise it adds cold start with no benefit.

### 8.6 CHORUS Phase 2 (out of scope)

Distributed transport not built. Single-process D understates full ChorusGraph advantage per original handoff.

---

## 9. Acceptance checklist (updated)

### Part A

- [x] Cortex native **128-d** from `raw_384`
- [x] Volume 900 tasks completed (JSONL on disk)
- [x] Bands 20/40 aggregate analysis usable
- [ ] Band 60 clean paired run (quota)
- [ ] `docs/BENCHMARK_RESULTS.md` updated with H12 volume
- [ ] Release tag (Director approval)

### Part B

- [x] C competent — tools + handoffs verified (`FAIR_BASELINE_C.md`)
- [x] D envelope pipeline — nodes, artifacts, runner
- [x] Shared abstain gate
- [x] Offline tests green
- [x] Live dry-runs executed (multiple iterations)
- [x] Per-hop + depth sweep measurement + `embed_count`
- [ ] **Envelope read path implemented**
- [ ] **Cache gate on healthcare hops (or explicit skip rationale)**
- [ ] **Thesis chart: D flatter than C as depth grows** — at ≥60 cases
- [ ] **Honest report if thesis fails after correct implementation**

---

## 10. Commands reference

```powershell
# API key (use default when primary exhausted)
$env:GEMINI_API_KEY = (Get-Content .env | Where-Object { $_ -match '^GEMINI_API_KEY_default=' } | ForEach-Object { $_.Split('=',2)[1].Trim() })

# Offline tests
python -m pytest tests/test_multiagent_pipeline.py tests/test_container_d_artifacts.py tests/test_healthcare_envelope_runtime.py tests/test_cortex_projector.py tests/test_cortex_compat.py -q

# Multi-agent C vs D
python -m benchmark.run_multiagent --cases 12 --output-dir benchmark/results/h13_multiagent_fixed
python -m benchmark.run_multiagent --cases 60 --output-dir benchmark/results/h13_multiagent_60  # recommended next scale

# Volume (resume default)
python -m benchmark.run_volume --tasks 300 --bands 20,40,60 --output-dir benchmark/results/h12_volume_300 --seed 42 --run-label H13

# Rebuild volume aggregate (no re-run)
python -m benchmark.rebuild_analysis benchmark/results/h12_volume_300 20,40,60 --tasks 300 --seed 42

# Verify Gemini keys
python scripts/verify_gemini_keys.py
```

---

## 11. Key file paths

| Purpose | Path |
|---------|------|
| H13 original spec | `handoffs/handoffH13.md` |
| This return | `handoffs/handoffbackH13.md` |
| C baseline | `benchmark/container_c/runner.py` |
| D pipeline | `benchmark/container_d/nodes.py`, `artifacts.py`, `runner.py` |
| Shared abstain | `benchmark/healthcare/abstain.py` |
| Harness | `benchmark/run_multiagent.py` |
| Latest multi-agent results | `benchmark/results/h13_multiagent_fixed/` |
| Volume results | `benchmark/results/h12_volume_300/aggregate_analysis.json` |
| Finance fairness | `benchmark/FAIRNESS_H9.md` |
| Design intent | `docs/DESIGN_v0.2.md` §7.6–7.7 |
| Cache gate (finance) | `chorusgraph/examples/finance_agent/nodes.py` `make_cache_gate_handler` |

---

## 12. Decisions / blockers

| Item | Status |
|------|--------|
| Thesis proven? | **No** — report honestly |
| Primary Gemini key | Exhausted (10k/day); use `GEMINI_API_KEY_default` |
| Band 60 volume | Quota-blocked; re-run on paid tier |
| Release tag | Director approval pending |
| Next engineering priority | **Envelope read + healthcare cache gate**, not more dry-runs |
| CHORUS distributed | Phase 2 — not built |

---

## 13. Message to successor

You inherited a **working rig** and a **broken thesis demonstration**. Container D was measuring "JSON prompts + unused vectors," not ChorusGraph M2M communication. The critical bugs (write-only envelopes, analyze handoff dropping retrieve, orphan ingress, JSON API mismatch) are fixed in code, but **the architectural gap remains**: D does not yet **read** envelopes or **skip** LLM work the way Container B does via `cache_gate`.

**The result we need:** At depth 6, D `tokens_in` and/or latency **flat or decreasing** vs C's growth curve — ideally with cache hits on repeated envelope patterns. Until the read path and cache gate exist, more 12-case runs will only produce noisy Gemini variance.

**Do not ship conclusions.** Fix the architecture, then run ≥60 cases on a paid key.

---

*Handoff H13 return · Part A mostly done · Part B rig live · thesis NOT proven · root causes documented · next: envelope read + healthcare cache gate.*

---

## 14. Follow-up — Finance E/F (H14)

Healthcare C/D was the wrong comparison for the Chorus speed thesis. **Finance multi-agent E vs F** uses the **same workload as A/B**:

| | Single-agent | Multi-agent |
|--|--------------|-------------|
| LangGraph | A | **E** |
| ChorusGraph | B | **F** |

See **`handoffs/handoffEF_finance_multiagent.md`** for full spec and run commands.

```powershell
python -m benchmark.run_finance_multiagent --tasks 60 --band 40 --output-dir benchmark/results/h14_finance_multiagent
```
