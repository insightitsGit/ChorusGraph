# HC2 vs HL2 — success gap and Prism Resonance

Canonical run `20260704_212111` (40 tasks, 40% repeat band, Azure ACI, commit `f43f532`):

| Metric | HL2 | HC2 |
|--------|-----|-----|
| Task success | **57.5%** | **87.5%** |
| Cache hit rate | 0% | **25%** |
| Abstain rate | 10% | **5%** |
| Mean LLM calls | 3.85 | **3.48** |
| Mean latency | 11,150 ms | 11,546 ms |

HC2 **wins on success** after Bug-1 fix (663edf7): facts-only cache + depth-aware judgment replay. Lower cache hit vs pre-fix run `20260703_042206` (62.5%) is intentional — `cache_payload_sufficient` rejects shallow hits that inflated cache but hurt accuracy.

## Is Prism Resonance used to improve success?

**No — not in HC2.**

| Mechanism | Where | HC2? | Improves success? |
|-----------|-------|------|-------------------|
| **Resonance bus routing** (`bus.subscribers_for_slug` → `route_via=resonance`) | `chorusgraph/core/ir.py` | **No** — HC2 uses native `core.Graph`, linear edges | Only when Resonance routing is wired |
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

### 2. Cache replay routing (Bug-1 fix, 2026-07-04)

On cache hit with **facts only** (archetype C):

- **Never** replay writer response (`cached_response_from_state` → `None`).
- **Skip** fact hops (intake/retrieve/drug_check) — prefilled from global cache.
- **Enter at first judgment hop:** depth 6 → **`analyze` → drug_check → safety → writer** (analyze is never cached; old code incorrectly jumped to `safety` first).
- Semantic gate uses `cache_query_key(case)`; **`cache_payload_sufficient`** rejects hits whose cached facts lack `retrieve` for depth ≥ 4 (blocks intake-only d2 seeds from satisfying d4/d6).

### 3. Cross-depth cache pollution — mitigated

Gate lookup and seeding use depth-suffixed keys only. Plain `topic:canonical` keys are no longer seeded for semantic slug. Payload sufficiency check rejects intake-only hits at depth 6.

### 4. Structured JSON handoffs vs HL2 prose

HC2 uses `INTAKE_D_SYSTEM` … `WRITER_D_SYSTEM` with `parse_json_object`. Malformed or empty JSON artifacts degrade downstream hops; HL2 uses free-text summaries that are more forgiving.

## What would actually help success (not resonance)

1. **Depth-aware writer** — only require safety verdict when `pipeline_depth == 6`; otherwise use HL2-style writer input.
2. **Cache replay validation** — on hit, require `hop_artifacts` to satisfy current depth (or re-run missing hops instead of writer-only).
3. **Stop seeding plain paraphrase keys** without depth suffix (or verify depth on gate hit).
4. **Re-score on cache hit** — run `score_healthcare_answer` before accepting cached `response`; miss → cold path.
5. **Migrate HC2 to `core.Graph`** — enables resonance routing per hop slug, but **routing alone won’t fix** the writer/safety mismatch; that’s a prompt/pipeline issue.

## Fair comparison note

HC2 is a **native ChorusGraph** scenario (`chorusgraph.core.Graph` + envelope handoffs). Success comparison to HL2 should treat cache + D-prompts as the intentional delta, not engine scheduling.
