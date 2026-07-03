# Sample data for benchmarks and tests

Synthetic finance and healthcare corpora used by all eight MVP scenarios (FL1–HC2).

## Finance (`benchmark/finance/corpus.py`)

| Category | Count | Notes |
|----------|-------|-------|
| FX canonical intents | 8 | USD/EUR, USD/GBP, EUR/GBP, USD/JPY, USD/CHF, USD/CAD, EUR/JPY, compare |
| Compound scenarios | 3 | $10k/5%/3y, $50k/6%/10y, $25k/4.5%/5y |
| Memory profiles | 5 | Risk, horizon, house goal, EUR income, fixed pension |
| Total phrasings | 40+ | 3–5 paraphrases per intent for cache/repeat testing |

Imported by `benchmark/workload.py` → `generate_workload()`.

### Cache seeding (from H9/H10/H11 benchmarks)

| Pattern | Where | What gets seeded |
|---------|-------|------------------|
| Finance multi-phrase | FC1/FC2 after tool | `message` + all `CANONICAL_QUERIES[canonical_id]` phrases |
| Finance novel-only | `--cache-seed-mode novel-only` | First phrase only (held-out paraphrase test) |
| Compound multi-phrase | FC1 compound_tool | Same pattern, `compound_savings` slug |
| Healthcare depth-aware | HC2 after writer | presentation + paraphrases + `[pipeline_depth=N]` keys |
| Offline warm | `warm_finance_corpus_cache()` | Pre-seed from corpus without LLM (stub or live FX) |

Implementation: `benchmark/shared/corpus_seed.py`

```powershell
# Warm finance cache from corpus (offline, no Gemini)
python -c "from chorusgraph.examples.finance_agent.runtime import FinanceRuntime; from benchmark.shared.corpus_seed import warm_finance_corpus_cache; r=FinanceRuntime(tenant_id='warm'); print(warm_finance_corpus_cache(r))"
```

## Healthcare (`benchmark/healthcare/cases.py` + `kb.py`)

| Category | Count | Notes |
|----------|-------|-------|
| Clinical cases | 20 | Anticoagulation, diabetes, HTN, HF, pregnancy, psych, nephrology, pulm, ID |
| Abstain cases | 4 | Unproven therapy, off-label chemo, lunar dosing, pediatric dosing without refs |
| Paraphrases | 3 per case | All cases including abstain — semantic cache targets |
| Guideline snippets | 21 | Topic-tagged retrieval corpus |
| Drug interactions | 9 | Major/moderate pairs aligned with case drugs |

Imported by `benchmark/healthcare_workload.py` → `generate_healthcare_workload()`.

## Quick stats (offline)

```powershell
python -c "from benchmark.finance.corpus import corpus_stats; print(corpus_stats())"
python -c "from benchmark.healthcare.cases import corpus_stats; print(corpus_stats())"
```

## Tests

`tests/test_sample_data.py` validates minimum richness, KB coverage, and rubric support.
