# HC2 vs HL2 — success gap and Prism Resonance

Canonical run `20260703_042206` (40 tasks, 40% repeat band):

| Metric | HL2 | HC2 |
|--------|-----|-----|
| Task success | **57.5%** | **45.0%** |
| Cache hit rate | 0% | **62.5%** |
| Abstain rate | 10% | 2.5% |
| Mean LLM calls | 3.85 | 1.02 |

HC2 wins on latency/cost but **loses on success** — mostly because of how cache + prompts interact, not missing engine magic.

## Is Prism Resonance used to improve success?

**No — not in HC2.**

| Mechanism | Where | HC2? | Improves success? |
|-----------|-------|------|-------------------|
| **Resonance bus routing** (`bus.subscribers_for_slug` → `route_via=resonance`) | `chorusgraph/core/ir.py` | **No** — HC2 uses **LangGraph** `StateGraph`, linear edges | Only in native `core.Graph` (HC1) |
| **Cache semantic match** (`cache._resonance.query`) | `chorusgraph/cache_gate/` | Yes — finds similar cached payloads | **Latency only**; can **hurt** success on bad replay |
| **resonance_rerank** | `chorusgraph/nodes/retrieve.py` | Not wired in healthcare | N/A |
| **Envelope projector** | HC2 `_envelope_update` | Yes — 64-d vectors for handoffs | Structure/logging, not routing |

Prism Resonance in the cache gate is **similarity retrieval**, not agent routing or evidence reranking. There is no resonance-based “pick the better path” logic in HC2.

## Root causes of lower HC2 success

### 1. Writer prompt requires safety; shallow pipelines skip safety (primary)

```133:137:benchmark/healthcare_workload.py
PIPELINE_AGENTS: dict[int, List[str]] = {
    2: ["intake", "writer"],
    4: ["intake", "retrieve", "analyze", "writer"],
    6: ["intake", "retrieve", "analyze", "drug_check", "safety", "writer"],
}
```

`WRITER_D_SYSTEM` expects an upstream **safety verdict**, but depth **2** and **4** never run `safety`. The writer often refuses:

> *"Cannot provide a recommendation without an upstream safety verdict."*

HL2 uses plain `WRITER_SYSTEM` with analysis/guidelines/interactions — **no safety prerequisite** — so it succeeds more often on the same cases.

### 2. Cache replay skips the full pipeline (repeat band)

On cache hit, `route_after_cache_hc2` jumps **cache_gate → writer**, skipping intake→…→safety.

| Variant | HC2 cache hit | HC2 success |
|---------|---------------|-------------|
| exact_repeat | **100%** | **27.3%** |
| paraphrase | **100%** | 55.6% |
| novel | 25% | 50.0% |

**10 paired cases:** HL2 succeeded, HC2 failed — **all 10 were cache hits** on repeat/paraphrase. Cached `hop_artifacts` often lack `safety` (seeded from depth-2/4 runs), so the writer refuses even though HL2 ran the full cold path.

### 3. Cross-depth cache pollution (secondary)

`healthcare_cache_query_keys` seeds **plain paraphrases without `[pipeline_depth=N]`** in addition to depth-suffixed keys. Semantic gate can match a shallow-depth payload when a deeper pipeline runs.

### 4. Structured JSON handoffs vs HL2 prose

HC2 uses `INTAKE_D_SYSTEM` … `WRITER_D_SYSTEM` with `parse_json_object`. Malformed or empty JSON artifacts degrade downstream hops; HL2 uses free-text summaries that are more forgiving.

## What would actually help success (not resonance)

1. **Depth-aware writer** — only require safety verdict when `pipeline_depth == 6`; otherwise use HL2-style writer input.
2. **Cache replay validation** — on hit, require `hop_artifacts` to satisfy current depth (or re-run missing hops instead of writer-only).
3. **Stop seeding plain paraphrase keys** without depth suffix (or verify depth on gate hit).
4. **Re-score on cache hit** — run `score_healthcare_answer` before accepting cached `response`; miss → cold path.
5. **Migrate HC2 to `core.Graph`** — enables resonance routing per hop slug, but **routing alone won’t fix** the writer/safety mismatch; that’s a prompt/pipeline issue.

## Fair comparison note

HC2 is **not** a pure ChorusGraph native scenario today — it still uses LangGraph `StateGraph` (same as FC2). Success comparison to HL2 should treat cache + D-prompts as the intentional delta, not engine scheduling.
