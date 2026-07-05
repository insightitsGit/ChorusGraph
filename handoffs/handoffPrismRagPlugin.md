# Handoff PrismRagPlugin — promote PrismRAG retrieval from benchmark-only to a swappable library backend

**Director:** Amin · **Architect:** Claude · **Engineer:** Cursor
**Refs:** [`chorusgraph/compose/ports.py`](../chorusgraph/compose/ports.py) (the `CacheBackend`/`MemoryBackend`/
`ToolBackend` pattern this mirrors) · [`chorusgraph/compose/stack.py`](../chorusgraph/compose/stack.py) ·
[`chorusgraph/nodes/retrieve.py`](../chorusgraph/nodes/retrieve.py) (existing L2 hook, currently unused
by the product) · [`docs/CACHE_PROFILES.md`](../docs/CACHE_PROFILES.md) · `handoffPrismRagAddition.md`
(where PrismRAG was first wired, benchmark-only)
**Date issued:** 2026-07-04

---

## 0. Why (verified, not assumed)

Checked before writing this: `grep -rl "PrismRAG\|prismrag" chorusgraph/` returns only
`chorusgraph/nodes/retrieve.py` (a docstring reference) — **the actual PrismRAG wiring
(`prismrag_patch.PrismRAGPatch` + Chroma vector store + taxonomy remap) lives entirely in
`benchmark/healthcare/kb_vector.py` + `prismrag_mapping.py` + `retrieval.py`.** It is benchmark-only —
not something a ChorusGraph user gets by installing the library. The Director wants it promoted to a
first-class, swappable backend, following the **exact pattern already proven** for caching:
`CacheBackend` (Protocol) → `PrismCacheBackend` (default) / `RedisCacheBackend` (swap) →
`ChorusStack.resolve_cache()` / `with_cache()`.

**Standing rules:** deterministic-first (retrieval has no LLM call — keep it that way) · Prism-native
comms unaffected (this is a node-entry data source, not a channel) · no mocks/fakes — a real Chroma
instance or recorded fixtures, never fabricated retrieval results · benchmark fairness: **LangGraph
baselines (HL1/HL2) are not touched** — only HC1/HC2 migrate to consume the new library surface ·
full `python -m pytest tests/ -q` green after every task · commit/push only when the Director asks
(trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`).

---

## 1. The port

**File:** `chorusgraph/compose/ports.py` (extend, same file as `CacheBackend`/`MemoryBackend`/`ToolBackend`)

```python
@runtime_checkable
class RetrievalBackend(Protocol):
    """
    L2 retrieval port — default: keyword stand-in (zero dependencies).
    Swap for PrismRAGRetrievalBackend for real vector search + taxonomy-aware re-embedding.
    """
    name: str

    def retrieve(self, topic: str, query: str, *, top_k: int = 6) -> List[Dict[str, Any]]:
        """Return ranked chunks: at least {id, topic, text, source, category_slug, score}."""

    def index(self, corpus: Sequence[Dict[str, Any]]) -> None:
        """(Re)build the backend's index from a corpus of {id, topic, text, source} records."""
```

Add `is_retrieval_backend(obj)` helper mirroring `is_cache_backend`. Export from `ports.py` `__all__`.

---

## 2. Default adapter — zero-dependency keyword stand-in

**File:** new `chorusgraph/compose/adapters/keyword_retrieval.py`

Generalize `benchmark/healthcare/tools.py::retrieve_guidelines` (currently hardcoded to the healthcare
`GUIDELINES` list) into a **corpus-agnostic** keyword-overlap retriever:

```python
class KeywordRetrievalBackend:
    name = "keyword"
    def __init__(self) -> None:
        self._corpus: List[Dict[str, Any]] = []
    def index(self, corpus): self._corpus = list(corpus)
    def retrieve(self, topic, query, *, top_k=6) -> List[Dict[str, Any]]:
        # same token-overlap + topic-match scoring as today's retrieve_guidelines,
        # generalized to self._corpus instead of the module-level GUIDELINES import.
```

This becomes the **default** — no chromadb, no PrismRAG license required. Matches the "batteries
included, batteries swappable" philosophy already established for `CacheBackend`.

---

## 3. PrismRAG adapter — the real backend, generalized off the healthcare corpus

**File:** new `chorusgraph/compose/adapters/prismrag_retrieval.py`

Promote `benchmark/healthcare/kb_vector.py` (Chroma vector store) + `prismrag_mapping.py`
(`PrismRAGPatch` construction, category assignment) into a general-purpose backend — **remove the
hardcoded `from benchmark.healthcare.kb import GUIDELINES` import**; the corpus and category rules
become constructor arguments:

```python
class PrismRAGRetrievalBackend:
    """Real vector search (Chroma) + PrismRAG taxonomy-aware re-embedding."""
    name = "prismrag"

    def __init__(
        self,
        *,
        embedder: Any,                       # reuse chorusgraph.embedders — embed-once discipline
        mapping: dict | "Mapping",            # PrismRAG category + rule definition (see below)
        license_key: Optional[str] = None,    # env PRISMRAG_LICENSE_KEY if not passed
        alpha: float = 0.25,
        collection_name: str = "chorusgraph_retrieval",
    ) -> None: ...
    def index(self, corpus: Sequence[Dict[str, Any]]) -> None: ...   # Chroma .add() with PrismRAG remap
    def retrieve(self, topic, query, *, top_k=6) -> List[Dict[str, Any]]: ...  # Chroma .query() with remap
```

Verify the real `prismrag_patch.PrismRAGPatch` / `Mapping` / `ChromaAdapter` signatures with `inspect`
before coding (library at `C:\code\PrismRagLib`, package `prismrag-patch`) — do not assume the shape
from the benchmark code without checking it still matches.

**Graceful degradation (mirror `RedisCacheBackend`'s pattern for missing `redis`):** if `chromadb` isn't
installed, or `license_key` is missing/invalid, **do not crash construction and do not fabricate a
license**. Log a clear one-line warning naming the missing piece (`"chromadb not installed — pip install
chorusgraph[retrieval]"` / `"no PRISMRAG_LICENSE_KEY — falling back to keyword retrieval"`) and fall back
to wrapping a `KeywordRetrievalBackend` internally for the `.retrieve()`/`.index()` calls. This is a
product-UX decision (fail loud in logs, not in the caller's face) — flag if you think fail-hard is
better and why.

---

## 4. Wire into ChorusStack

**File:** `chorusgraph/compose/stack.py`, `chorusgraph/compose/defaults.py`

1. `ChorusStack`: add `retrieval: Optional[RetrievalBackend] = None` field + `resolve_retrieval()`
   method (mirrors `resolve_cache()`) defaulting to `default_retrieval_backend()`.
2. `compose/defaults.py`: `default_retrieval_backend() -> KeywordRetrievalBackend` (the zero-dependency
   default — mirrors how `default_prism_cache_backend` is the cache default, but here the *product*
   default is the cheap one; PrismRAG is an explicit opt-in swap, since it needs a license).
3. `with_retrieval(backend)` swap method — **use `dataclasses.replace(self, retrieval=backend)`**, not
   a hand-copied field list (this is the exact bug Improve-2 T2 already found and fixed for
   `with_cache` — don't reintroduce it here).
4. A new `to_retrieve_handler(topic, top_k)` method on `ChorusStack` (mirrors `to_cache_runtime()`)
   that builds a ready-to-use retrieve node via `chorusgraph.nodes.retrieve.make_retrieve_handler`,
   wired to `self.resolve_retrieval().retrieve`.

**Exit:** unit tests mirroring `test_compose_stack.py`'s Redis-swap test: defaults resolve to
`KeywordRetrievalBackend`, `with_retrieval(PrismRAGRetrievalBackend(...))` swaps cleanly (all other
fields preserved — the programmatic all-fields-except-one regression guard from Improve-2 T2 applies
here too), `to_retrieve_handler` produces a working node.

---

## 5. Migrate HC1/HC2 to consume the library surface (dogfood the plug-in)

**Files:** `benchmark/hc1/*`, `benchmark/hc2/nodes.py`, `benchmark/healthcare/prismrag_mapping.py`
(trim, don't delete — domain config stays benchmark-owned)

Replace HC1/HC2's direct use of `benchmark/healthcare/kb_vector.py`/`retrieval.py` with:
```python
stack = ChorusStack.defaults(tenant_id=...).with_retrieval(
    PrismRAGRetrievalBackend(embedder=..., mapping=CLINICAL_CATEGORY_RULES, license_key=...)
)
stack.resolve_retrieval().index(GUIDELINES)   # domain corpus stays benchmark-owned
retrieve_node = stack.to_retrieve_handler(topic="clinical_guidelines", top_k=6)
```
`CLINICAL_CATEGORY_RULES` and `GUIDELINES` (both domain-specific data, not machinery) stay in
`benchmark/healthcare/`. **Delete** `benchmark/healthcare/kb_vector.py`'s Chroma/PrismRAGPatch
construction code once HC1/HC2 run on the library version — don't leave two parallel implementations.

**Fairness constraint, restated:** HL1/HL2 keep their own existing tool-based retrieval untouched.
Only the ChorusGraph-side scenarios change *how* they get PrismRAG, not *whether* they had it.

**Exit:** HC1/HC2 offline tests (stub LLM) pass on the migrated wiring; a real (or recorded-fixture)
Chroma-backed retrieval run produces the same shape of results as before migration — re-run the H21
depth-6 offline proof test to confirm no regression from the promotion.

---

## 6. Docs

- `docs/CACHE_PROFILES.md` §4: note that `retrieve` hops now source from a swappable `RetrievalBackend`,
  not a benchmark-only helper.
- `docs/ENGINE_DESIGN_v0.1.md` / composite-layer section: add `RetrievalBackend` to the ports table
  alongside `CacheBackend`/`MemoryBackend`/`ToolBackend`.
- New: a short `docs/PLUGINS.md` or a section in the compose docstring listing all four ports and their
  defaults/swap options in one place — a user evaluating "what can I bring my own of" should find one
  answer, not have to read four files.

---

## Order & effort

§1 port (½ d) → §2 default adapter (½ d) → §3 PrismRAG adapter (1–1.5 d, most of it verifying the real
`prismrag_patch` signatures) → §4 ChorusStack wiring (½ d) → §5 HC1/HC2 migration (1 d) → §6 docs.

## Return format (`handoffbackPrismRagPlugin.md`)

Per section: files · exit criteria pass/fail with real command output · actual `prismrag_patch`
signatures verified vs assumed (flag deviations) · confirm the graceful-degradation behavior chosen
(fallback vs fail-hard) and why · confirm `dataclasses.replace` used for `with_retrieval` (not a hand
copy) · confirm the duplicate benchmark-only PrismRAG code was deleted, not left parallel · anything
blocked, stated plainly. No commits unless the Director asks.

---
*PrismRagPlugin · promotes PrismRAG from a benchmark-only helper to the fourth swappable ChorusStack
port (`RetrievalBackend`, alongside Cache/Memory/Tool) · zero-dependency keyword default, PrismRAG as
an explicit opt-in swap · HC1/HC2 migrate to dogfood it; HL1/HL2 untouched.*
