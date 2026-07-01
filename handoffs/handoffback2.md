# Handoff 2 — Return · Senior Engineer (Cursor) → Architect

## 1. Summary

Implemented **ADR-002 in executable form**: a two-stage `cache_gate` wrapping real `PrismCache` (64-d coarse recall → 384-d verify → policy-gated decision), a Pydantic `Section` schema, embedder fail-loud guard, ChorusGraph **sidecar store** for Stage-2 raw embeddings, ledger `cache_hit`/`cache_score` instrumentation, and a **shadow-mode harness** with a real labeled dataset (43 cases × 5 verify thresholds = 215 rows). Shadow mode **logs only — never serves** from cache.

Local proxy measurement at `COARSE_THRESHOLD=0.88`: **FP = 0** on all fp-eligible hits; hit-rate `h` is low (0–25% per slug) because 0.88 coarse is strict for paraphrase distance in the proxy dataset. **This is not production traffic** — the Azure replay is still required for the real `(h, FP)` frontier.

## 2. File tree

```
C:\code\ChorusGraph\
├── pyproject.toml                          # v0.2.0, numpy + prismlang deps
├── chorusgraph/
│   ├── embedders.py                        # PrismlangOnnxEmbedder (real MiniLM ONNX)
│   ├── sections/
│   │   ├── __init__.py
│   │   └── models.py                       # Section, CachePolicy
│   ├── cache_gate/
│   │   ├── __init__.py
│   │   ├── decision.py                     # Decision, DecisionKind
│   │   ├── gate.py                         # gate() — §5 algorithm
│   │   ├── backend.py                      # recall(), seed_cache_entry()
│   │   └── sidecar.py                      # SidecarStore (384-d + slug)
│   ├── policy/
│   │   ├── __init__.py
│   │   └── embedder_guard.py               # HashEmbedder block + canary
│   ├── shadow/
│   │   ├── __init__.py
│   │   ├── harness.py                      # run_shadow_measurement(), CLI
│   │   ├── report.py                       # (h, FP) frontier aggregation
│   │   ├── results_store.py                # shadow_results SQLite table
│   │   └── dataset/
│   │       └── labeled_queries.json        # 10 clusters, 43 labeled cases
│   └── ledger/
│       └── instrument.py                   # make_cache_gate_step(), annotate_cache_step
├── tests/
│   ├── test_cache_gate.py
│   ├── test_shadow.py
│   └── test_sections.py
└── handoffs/
    └── handoffback2.md                     # this file
```

## 3. How to run

```powershell
cd C:\code\ChorusGraph
pip install -e ".[dev]"
# Requires `prism` package (PrismCache) on PYTHONPATH / site-packages

pytest -v

# Shadow measurement (logs only, never serves)
python -m chorusgraph.shadow.harness
# or: chorusgraph-shadow
```

## 4. Test results

```
============================= test session starts =============================
collected 19 items

tests/test_adapter.py ....                               [ 21%]
tests/test_cache_gate.py .......                         [ 57%]
tests/test_ledger.py .s                                  [ 68%]
tests/test_sections.py ..                                [ 78%]
tests/test_shadow.py ....                               [100%]

======================== 18 passed, 1 skipped in ~3.7s ========================
```

### Shadow `(h, FP)` table — LOCAL PROXY (COARSE=0.88, real ONNX embedder)

```
slug                   verify        h       FP   hits  fp_n     n
------------------------------------------------------------------------
company_info             0.90    0.000    0.000      0     0     4
company_info             0.93    0.000    0.000      0     0     4
company_info             0.95    0.000    0.000      0     0     4
company_info             0.97    0.000    0.000      0     0     4
company_info             0.99    0.000    0.000      0     0     4
developer_ecosystem      0.90    0.250    0.000      1     0     4
developer_ecosystem      0.93    0.250    0.000      1     0     4
developer_ecosystem      0.95    0.250    0.000      1     0     4
developer_ecosystem      0.97    0.000    0.000      0     0     4
developer_ecosystem      0.99    0.000    0.000      0     0     4
general                  0.90    0.000    0.000      0     0     4
general                  0.93    0.000    0.000      0     0     4
general                  0.95    0.000    0.000      0     0     4
general                  0.97    0.000    0.000      0     0     4
general                  0.99    0.000    0.000      0     0     4
greeting                 0.90    0.200    0.000      1     0     5
greeting                 0.93    0.000    0.000      0     0     5
greeting                 0.95    0.000    0.000      0     0     5
greeting                 0.97    0.000    0.000      0     0     5
greeting                 0.99    0.000    0.000      0     0     5
platform_products        0.90    0.200    0.000      1     0     5
platform_products        0.93    0.000    0.000      0     0     5
platform_products        0.95    0.000    0.000      0     0     5
platform_products        0.97    0.000    0.000      0     0     5
platform_products        0.99    0.000    0.000      0     0     5
pricing                  0.90    0.200    0.000      1     0     5
pricing                  0.93    0.200    0.000      1     0     5
pricing                  0.95    0.200    0.000      1     0     5
pricing                  0.97    0.000    0.000      0     0     5
pricing                  0.99    0.000    0.000      0     0     5
research_tools           0.90    0.000    0.000      0     0     4
research_tools           0.93    0.000    0.000      0     0     4
research_tools           0.95    0.000    0.000      0     0     4
research_tools           0.97    0.000    0.000      0     0     4
research_tools           0.99    0.000    0.000      0     0     4
routing                  0.90    0.250    0.000      1     0     4
routing                  0.93    0.000    0.000      0     0     4
routing                  0.95    0.000    0.000      0     0     4
routing                  0.97    0.000    0.000      0     0     4
routing                  0.99    0.000    0.000      0     0     4
vertical_agents          0.90    0.000    0.000      0     0     4
vertical_agents          0.93    0.000    0.000      0     0     4
vertical_agents          0.95    0.000    0.000      0     0     4
vertical_agents          0.97    0.000    0.000      0     0     4
vertical_agents          0.99    0.000    0.000      0     0     4
web_search               0.90    0.000    0.000      0     0     4
web_search               0.93    0.000    0.000      0     0     4
web_search               0.95    0.000    0.000      0     0     4
web_search               0.97    0.000    0.000      0     0     4
web_search               0.99    0.000    0.000      0     0     4
```

**fp-eligible hits at verify=0.95 (all correct):**
- `pricing` / "what is the price of meeting scheduler" — coarse 0.974, verify 0.958 → match
- `developer_ecosystem` / "pip install command for prismlang" — coarse 0.960, verify 0.963 → match

**Ledger:** 43 `cache_gate` steps with `cache_hit` and `cache_score` populated during shadow run.

## 5. Key decisions & deviations

| Decision | Rationale |
|----------|-----------|
| **ChorusGraph sidecar stores 384-d at seed time** | PrismCache `CacheEntry` stores `query_text` + response only — no raw 384-d vector. Re-embedding `query_text` is deterministic but Stage-2 must compare against the *original* query embedding per ADR-002. Sidecar keyed by `packet_id` stores `raw_embedding` (1536 bytes/float32×384), `category_slug`, `cache_policy`. |
| **`PrismlangOnnxEmbedder` as default** | Same all-MiniLM-L6-v2 model as `SentenceTransformerEmbedder`; `sentence-transformers` failed on this machine (HF hub 404 on chat templates). ONNX path via `prismlang.encoder` passes canary (cosine > 0.5) and is semantically real — not HashEmbedder. |
| **Read-only PrismCache access** | `recall()` uses `cache._resonance.query()` + `cache._store.load()` — same path as `get_or_call` Stage 1, no PrismCache modification. |
| **`seed_cache_entry()` for shadow** | Populates cache via `cache._store_response()` + sidecar — no LLM, no serve. |
| **FP numerator excludes `semantic` policy** | Per §6: generative sections ineligible for verbatim FP counting; `HIT_AS_CONTEXT` tracked in `h` but not `fp_eligible`. |
| **Shadow only** | No live graph path calls `gate()` to skip work — harness logs decisions only. |

## 6. Blockers / issues hit

- **`sentence-transformers` HF hub failure** on dev machine — worked around with `PrismlangOnnxEmbedder` (same model weights via ONNX). Embedder guard accepts any non-Hash embedder passing canary, not only `SentenceTransformerEmbedder` by class name.
- **`prism` not on PyPI as `prism`** — installed from local/site-packages; not added to `pyproject.toml` (director namespace decision pending). Tests require `from prism.cache import PrismCache`.
- **Low local `h`** at coarse 0.88 — expected for a strict threshold + hand-authored paraphrases; not a bug. Azure traffic replay will give the real hit-rate curve.

## 7. Answers to §9 open questions

### Q1 — Stage-2 raw-embedding source?

**ChorusGraph sidecar store**, not PrismCache-native. PrismCache persists `query_text` but not the 384-d vector. Storage cost: **~1.5 KB/entry** (384 × float32) + slug/policy metadata. At 50k entries ≈ 75 MB — negligible vs response payloads. Alternative considered: re-embed `query_text` at verify time — rejected because tokenization/normalization drift could skew cosine vs the embedding used at cache-write.

### Q2 — Local `(h, FP)` frontier and threshold for FP < 1%?

At **COARSE=0.88**, local proxy shows **FP=0 everywhere** (0 fp-eligible mismatches out of 7 total fp-eligible hits across all thresholds). Highest `h` with FP=0:

| slug | best h | verify threshold |
|------|--------|------------------|
| developer_ecosystem | 0.25 | 0.90–0.95 |
| routing | 0.25 | 0.90 |
| greeting, pricing, platform_products | 0.20 | 0.90 (pricing also 0.93–0.95) |

**No slug needed verify > 0.95 to achieve FP < 1% locally** — but sample size is tiny (n=4–5 per slug). Do **not** treat this as production-safe.

### Q3 — Where did near-misses slip through?

**None in local proxy.** Near-miss traps (e.g. "how much is chorusmesh" vs meeting-scheduler canonical) failed at **Stage 1** (coarse ~0.45) — never reached verify. Cross-category traps (greeting query vs pricing section slug) blocked by **taxonomy guard**. Short paraphrases ("hi" vs "hello there") fail **Stage 2** (verify ~0.64) even when coarse passes — exactly the safety behavior §8.1 intends.

### Q4 — Recommended defaults for Azure run?

- **COARSE_THRESHOLD: 0.88** (matches dashboard hub operating point per DESIGN §0)
- **VERIFY_THRESHOLD: 0.95** start, sweep {0.90, 0.93, 0.95, 0.97, 0.99} per slug
- **Per-slug rollout:** only enable live cache-serve for a slug once Azure shadow shows FP < 1% at chosen verify

### Q5 — Proposed Handoff 3 scope?

1. **Wire `cache_gate` into adapter** as pre-node hook (still shadow-flagged, then per-slug live enable).
2. **Azure traffic replay harness** — ingest real Dashboard/Website Hub query logs into shadow dataset.
3. **`PrismCheckpointer`** skeleton (section snapshots + graph position on Postgres).
4. **Postgres ledger steps normalization** (ADR-003).
5. **Generative semantic FP** — LLM-judge or citation-diff for `semantic` policy (deferred from H2).

## 8. Design contradictions

1. **§5 algorithm `cache.recall(env, top_k=5)`** — PrismCache has no public `recall()` API; implemented via resonance query wrapper. Recommend adding `recall_candidates()` to PrismCache upstream.
2. **§5 `top.raw_embedding_384`** — does not exist on PrismCache entries; sidecar is required unless PrismCache is extended.
3. **§5 `top.category_slug`** — not on `CacheEntry`; sidecar + taxonomy guard at gate-evaluation time using `Section.category_slug` vs sidecar slug.
4. **Low local `h` vs §15 "h ≈ 0.30 target"** — proxy dataset + strict 0.88 coarse explains gap; Azure measurement is mandatory before any cost claim.

## 9. Proposed scope for Handoff 3

See §7 Q5 above. Priority: **Azure shadow replay → per-slug live-enable flag → PrismCheckpointer**.

---

*Handoff 2 complete · 18 pytest passed · shadow-only · FP=0 local proxy · cache never served live.*
