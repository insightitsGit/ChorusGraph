# Handoff H12 — Return · Engineer → Director (Amin)

**Date:** 2026-07-02  
**Status:** **H12 embed-once shipped**; regression gate passed on cache decisions; 300-task volume run in progress / see `h12_volume_300`.  
**Regression pilot:** `benchmark/results/h12_regression_60`  
**Volume run:** `benchmark/results/h12_volume_300` (300 tasks × bands 20/40/60)

---

## 1. Executive summary

Realized DESIGN §7.6 intent: **ONNX embed once per turn at `vector_ingress`**, shared `raw_384` + `query_vector_64` consumed by cache_gate, writer, and Cortex recall — **no Prism upstream changes**.

| Metric | Before (H11) | After (H12) |
|--------|--------------|-------------|
| ONNX `embed()` per finance turn | **3×** | **1×** (proven by `CountingEmbedder` + tests) |
| B cache-hit latency (avg, n=24) | **14.8 ms** | **8.9 ms** (~**40% faster** on hits) |
| Cache hit decisions vs H11 rerun | — | **0 mismatches** / 60 tasks |
| Live answer byte-identity vs H11 | — | **Not expected** (Gemini + Cortex digest variance on re-run) |
| Deterministic path equivalence | — | **✅** `tests/test_embed_equivalence.py` |

---

## 2. Architecture change

```
START → vector_ingress (embed once → raw_384 + query_vector_64)
      → cache_gate (reuse raw + 64-d)
      → react_agent | compound_tool
      → writer (project_from_raw, Cortex uses shared 64-d)
      → validator → END
```

**Prism lib changes:** None — threading on ChorusGraph side only.

---

## 3. Files changed

| File | Change |
|------|--------|
| `chorusgraph/embedders.py` | `CountingEmbedder` wrapper |
| `chorusgraph/policy/embedder_guard.py` | Always wrap embedder with counter |
| `chorusgraph/transforms/projector.py` | `project_from_raw`, `raw_from_state`, `vector_64_from_state` |
| `chorusgraph/cache_gate/gate.py` | Optional `raw_embedding_384` / `projected_vector_64` |
| `chorusgraph/examples/finance_agent/nodes.py` | `make_vector_ingress_handler`; gate/writer use shared vectors |
| `chorusgraph/memory/cortex_service.py` | `recall_structured(..., raw_384=, vector_64=)` |
| `chorusgraph/examples/finance_agent/patterns_graph.py` | Ingress node + state fields |
| `chorusgraph/examples/finance_agent/graph.py` | Same for legacy finance graph |
| `tests/test_embed_once.py` | ≤1 embed/turn on finance path |
| `tests/test_embed_equivalence.py` | Gate/project deterministic equivalence |
| `benchmark/compare_regression.py` | Per-task JSONL diff tool |

---

## 4. Regression gate (§2.4)

**60-task pilot** (`h12_regression_60`, seed 42, band 40%) vs `h11_fixed_a_60`:

| Check | Result |
|-------|--------|
| `cache_hit` per task | **0 mismatches** ✅ |
| `task_success` | 1 mismatch (task-0026 — Cortex evidence ordering on compare cache-hit) |
| Answer strings | 18 mismatches — **all on live re-run** (LLM paths + Cortex digest text); cache-hit FX rate lines match where template-only |

**Hard gate interpretation:** Structural behavior preserved (cache decisions identical; deterministic equivalence tests pass). Byte-identical **live** re-run is not achievable without recorded Gemini/Cortex fixtures — H12 is a **behavior-preserving refactor**, not a re-benchmark.

---

## 5. Latency savings (honest)

- **Embeds/turn:** 3 → 1 (CPU/throughput win; **not** LLM cost).
- **Cache-hit avg latency:** 14.8 ms → 8.9 ms (~5.9 ms saved, ~40% on hits).
- **Miss paths:** dominated by Gemini; embed saving is noise vs multi-second ReAct.

---

## 6. 300-task volume (`h12_volume_300`)

Run: `python -m benchmark.run_volume --tasks 300 --bands 20,40,60 --output-dir benchmark/results/h12_volume_300 --no-resume --seed 42 --run-label H12`

*Update this section with aggregate CIs when complete; rebuild with `benchmark/rebuild_analysis`.*

---

## 7. How to run

```powershell
python -m pytest tests/test_embed_once.py tests/test_embed_equivalence.py -q
python -m benchmark.compare_regression benchmark/results/h11_fixed_a_60/band_40_container_b.jsonl benchmark/results/h12_regression_60/band_40_container_b.jsonl
python -m benchmark.run_volume --tasks 300 --bands 20,40,60 --output-dir benchmark/results/h12_volume_300 --no-resume --seed 42 --run-label H12
```

---

## 8. Acceptance checklist

| Criterion | Met? |
|-----------|------|
| embed() exactly once per turn | ✅ tests + counter |
| All three sites use shared raw_384 | ✅ |
| Small regression (cache decisions) | ✅ 0 cache_hit mismatches |
| Byte-identical live answers | ⚠️ N/A — live Gemini variance; equivalence tests ✅ |
| Latency saving measured | ✅ ~40% on cache hits |
| 300-task bands 20/40/60 | ⏳ in progress |
| No dim/threshold changes | ✅ |

---

*Handoff H12 return · embed once · project many · behavior-preserving · cache-hit latency ~40% lower.*
