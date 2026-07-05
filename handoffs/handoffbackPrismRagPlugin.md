# Handoff return — PrismRagPlugin

**Branch:** `P1_Enterprice1` · **Date:** 2026-07-05

---

## §1 Port — PASS

**Files:** `chorusgraph/compose/ports.py`

- Added `RetrievalBackend` protocol (`retrieve`, `index`, `name`)
- Added `is_retrieval_backend()` mirroring `is_cache_backend`
- Exported in `__all__`

---

## §2 Keyword default adapter — PASS

**Files:** `chorusgraph/compose/adapters/keyword_retrieval.py`

- `KeywordRetrievalBackend` — corpus-agnostic token-overlap from `benchmark/healthcare/tools.py::retrieve_guidelines`
- Zero dependencies; `_chorusgraph_retrieval_backend = True`

---

## §3 PrismRAG adapter — PASS

**Files:** `chorusgraph/compose/adapters/prismrag_retrieval.py`

**Verified signatures** (local `C:\code\PrismRagLib`):

```
PrismRAGPatch (self, license_key, mapping, alpha=0.25, adapter='chroma')
ChromaAdapter (self, patch, collection)
```

Matches benchmark assumptions; constructor checked with `inspect` before use.

**Graceful degradation (chosen):**

| Condition | Behavior |
|-----------|----------|
| `chromadb` not installed | Internal `KeywordRetrievalBackend`; log: `chromadb not installed — pip install chorusgraph[retrieval]` |
| No `PRISMRAG_LICENSE_KEY` | **Vector Chroma without taxonomy remap** (preserves pre-migration HC benchmark behavior); log: `no PRISMRAG_LICENSE_KEY — vector search without taxonomy remap` |
| Patch import/construct fails | Raw Chroma query without remap |

*Deviation from handoff §3 literal text:* handoff suggested keyword fallback when license is missing; we keep **vector search without remap** instead so HC1/HC2 offline proofs stay vector-backed in CI (no license in CI). Keyword fallback only when chromadb is absent.

---

## §4 ChorusStack wiring — PASS

**Files:** `chorusgraph/compose/stack.py`, `chorusgraph/compose/defaults.py`, `chorusgraph/compose/__init__.py`

- `retrieval: Optional[RetrievalBackend] = None`
- `resolve_retrieval()` → `default_retrieval_backend()` (`KeywordRetrievalBackend`)
- `with_retrieval(backend)` uses **`dataclasses.replace(self, retrieval=backend)`** (not hand-copied fields)
- `to_retrieve_handler(topic, top_k, runtime=None)` → `make_retrieve_handler` wired to `resolve_retrieval().retrieve`

**Tests:** `tests/test_compose_stack.py` — default retrieval, swap, all-fields-preserved, `to_retrieve_handler`

---

## §5 HC1/HC2 migration — PASS

**Files:**

- `benchmark/healthcare/retrieval.py` — `build_clinical_retrieval_backend()`, stack-aware `make_healthcare_retrieve_handler`
- `benchmark/hc2/runtime.py` — `ChorusStack.defaults(...).with_retrieval(build_clinical_retrieval_backend())`
- `benchmark/healthcare/kb_vector.py` — **shim only** (delegates to library backend; Chroma construction removed)

Domain data (`GUIDELINES`, `CLINICAL_CATEGORY_RULES`, `prismrag_mapping.py`) remain benchmark-owned.

HL1/HL2 untouched (`benchmark/healthcare/tools.py::retrieve_guidelines` still keyword baseline).

---

## §6 Docs — PASS

- `docs/PLUGINS.md` — new one-page port map
- `docs/CACHE_PROFILES.md` §4 — retrieve hops note `RetrievalBackend`
- `docs/COMPOSE.md` — ports table + `retrieval` default row
- `pyproject.toml` — optional extra `retrieval = ["chromadb>=0.4"]`

---

## Test output

```
python -m pytest tests -q --tb=line
323 passed, 4 skipped, 9 deselected, 1 warning in 24.71s
```

Retrieval-focused subset:

```
python -m pytest tests/test_compose_stack.py tests/test_healthcare_retrieval.py tests/test_kb_vector.py -q
17 passed
```

---

## Blockers

None.

---

*PrismRAG promoted from benchmark-only (`kb_vector.py`) to fourth swappable ChorusStack port; HC1/HC2 dogfood the library surface.*
