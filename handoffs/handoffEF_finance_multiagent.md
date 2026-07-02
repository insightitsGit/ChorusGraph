# Handoff — Finance Multi-Agent E vs F (H14)

**Date:** 2026-07-02  
**From:** Engineer (Cursor)  
**To:** Director / Successor  
**Context:** H13 healthcare C vs D did not prove the vector-substrate thesis. Root cause: wrong domain comparison (healthcare vs finance cache story) + broken D implementation. **E/F fixes the comparison design.**

---

## 1. Why E and F exist

| Container | Domain | Pattern | What it tests |
|-----------|--------|---------|---------------|
| **A** | Finance | Single-agent LangGraph ReAct | Baseline without Chorus |
| **B** | Finance | Single-agent ChorusGraph + cache | Cache fast path (~13 ms hits) |
| **C** | Healthcare | Multi-agent LangGraph | Wrong domain for finance thesis |
| **D** | Healthcare | Multi-agent ChorusGraph | Broken envelope read path in H13 |
| **E** | Finance | **Multi-agent LangGraph** | Growing context baseline |
| **F** | Finance | **Multi-agent ChorusGraph** | Envelope handoffs + cache_gate + Cortex |

**The fair comparison you wanted:**

```
Single-agent:  A  vs  B   (same finance workload — proven in H12 volume)
Multi-agent:   E  vs  F   (same finance workload — NEW in H14)
Cross-level:   B  vs  F   (both ChorusGraph; single vs multi hop structure)
Cross-level:   A  vs  E   (both LangGraph; ReAct vs linear pipeline)
```

Healthcare C/D remains useful for clinical safety/abstain — but **finance E/F is the correct place to test Chorus speed and token flattening.**

---

## 2. Architecture

### Pipeline (identical agent roles in E and F)

```
researcher → tool → writer → validator
```

Container F prepends:

```
vector_ingress → cache_gate → researcher → tool → writer → validator
```

### Container E — LangGraph baseline

- **File:** `benchmark/container_e/runner.py`
- **Handoffs:** Growing `context` string appended each hop (like C)
- **No cache, no Cortex** (like A)
- **Tools:** Called in code at tool hop (like C retrieve hop)

### Container F — ChorusGraph

- **Files:** `benchmark/container_f/nodes.py`, `artifacts.py`, `runner.py`
- **Handoffs:** `envelope_handoff(hop, envelope_id, hop_input)` — compact JSON per hop
- **Envelope store:** `session_tool_cache["env:{id}"]` — artifacts keyed by envelope_id
- **Cache gate:** Same as B — on hit, skip tool LLM path; template writer
- **Cortex:** Memory seed/recall like B
- **Cache seed:** After FX tool, seeds canonical paraphrases like B

---

## 3. Workload (same as A/B)

Uses `benchmark/workload.py` — **not** healthcare cases.

- FX queries: `usd_eur`, `usd_gbp`, `compare_usd_eur_gbp`, etc.
- Compound: `compound_savings`
- Memory: `memory_seed`, `memory_recall_cross`
- Repeat bands: 20/40/60% (default **40%** for cache story)

**Scoring:** `benchmark/measure.py` → `score_task_success` + `rubric.py` (identical to A/B).

---

## 4. How to run

```powershell
# API key (use default if primary exhausted)
$env:GEMINI_API_KEY = (Get-Content .env | Where-Object { $_ -match '^GEMINI_API_KEY_default=' } | ForEach-Object { $_.Split('=',2)[1].Trim() })

# Offline structure tests
python -m pytest tests/test_finance_multiagent.py -q

# Live E vs F (recommended: 60 tasks, band 40%)
python -m benchmark.run_finance_multiagent --tasks 60 --band 40 --output-dir benchmark/results/h14_finance_multiagent

# Compare to single-agent A/B on same band
python -m benchmark.run_volume --tasks 60 --bands 40 --output-dir benchmark/results/h14_single_agent_60 --seed 42 --run-label H14
```

---

## 5. What to measure (thesis chart)

### Primary (E vs F)

| Metric | Expected if thesis holds |
|--------|--------------------------|
| `tokens_in` on **exact_repeat** / **paraphrase** | F << E (bounded handoffs + cache) |
| `latency_ms` on repeats | F << E (cache hit → template writer, skip tool/researcher LLM) |
| `tokens_in` vs hop count | E grows with context; F flat per hop |
| `cache_hit_rate` (F only) | >0% after band-40 warm-up (like B) |

### Secondary (cross-level)

| Comparison | Question |
|------------|----------|
| B vs F | Does multi-agent envelope add overhead vs single-agent ReAct? |
| A vs E | ReAct loop vs fixed 4-hop — which uses fewer tokens? |
| B p50 vs F p50 on repeats | Does F match B's cache fast path? |

---

## 6. File tree

```
benchmark/
  finance_multiagent_shared.py   # state, record_hop, heuristic_tool_plan, validate_draft
  run_finance_multiagent.py      # E vs F harness
  container_e/
    runner.py
    prompts.py
    FAIR_BASELINE_E.md
  container_f/
    nodes.py
    artifacts.py
    runner.py
  measure.py                     # ContainerId extended: A,B,E,F + hop_metrics
tests/
  test_finance_multiagent.py
handoffs/
  handoffEF_finance_multiagent.md  # this file
```

---

## 7. Relationship to H13 healthcare C/D

| Issue | Healthcare C/D (H13) | Finance E/F (H14) |
|-------|----------------------|-------------------|
| Domain | Clinical pipeline | **Same as A/B** |
| Cache | None in C or D | **F has cache_gate like B** |
| Workload | 8 clinical cases | **300+ FX tasks, repeat bands** |
| Thesis test | Inconclusive | **Designed for cache + token flattening** |
| Envelope read | Was broken; partially fixed | **Store on write; compact hop_input on read** |

**Recommendation:** Pause healthcare C/D thesis claims. Prove Chorus on **finance E vs F** first. Revisit healthcare once envelope + cache pattern is validated in-domain.

---

## 8. Acceptance checklist

- [x] E built — LangGraph 4-hop finance pipeline
- [x] F built — envelope + cache_gate + Cortex
- [x] Same workload/scoring as A/B
- [x] Harness `run_finance_multiagent.py`
- [x] Offline tests
- [ ] Live run ≥60 tasks band 40% with results
- [ ] Compare E vs F repeat latency to B cache hits
- [ ] Document in `docs/BENCHMARK_RESULTS.md`

---

## 9. Known limitations

1. **Researcher uses LLM + heuristic fallback** — compare queries may need both tools; heuristic handles `compare_usd_eur_gbp`.
2. **F envelope read** — downstream hops use compact `hop_input`, not full artifact hydration from envelope_id (improvement path documented in H13 handoffback).
3. **Memory tasks** — F uses Cortex; E uses conversation history only (E will fail cross-session recall vs F — expected, same as A vs B).
4. **CHORUS transport** — not exercised (single-process only).

---

*H14 · Finance multi-agent E vs F · same domain as A/B · correct comparison for Chorus thesis.*
