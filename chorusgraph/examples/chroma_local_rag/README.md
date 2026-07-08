# Local RAG with Chroma + ChorusGraph

Local vector storage and native graph orchestration -- no LangGraph, no cloud API required.

## Prerequisites

- Python 3.11+

## Install

```bash
pip install "chorusgraph[retrieval]"
```

Optional: set `GEMINI_API_KEY` and `pip install "chorusgraph[gemini]"` for a richer LLM answer. The demo runs fully offline without it.

## Run

```bash
python -m chorusgraph.examples.chroma_local_rag.main
```

## Expected output

```
Query: What is the refund policy?

Retrieved chunks:
  1. Refund Policy: Customers may request a full refund within 30 days of purchase if they are not s... (score=0.812)
  2. Expense Reimbursement: Business expenses over $25 require an itemized receipt submitted within 3... (score=0.421)
  3. Paid Time Off: Full-time employees receive 20 days of paid time off per year, accrued monthly. U... (score=0.398)

Answer:
Based on the documents: Refund Policy: Customers may request a full refund within 30 days of purchase if they are not satisfied. Refunds are processed to the original payment method within 5-7 business days. Digital subscriptions are refundable only within the first 14 days.

Ledger path: retrieve -> answer
```

Scores and chunk order may vary slightly by embedder version.

## Architecture

Chroma stores document embeddings indexed through `PrismRAGRetrievalBackend`.
ChorusGraph runs a two-node native graph: `retrieve` fetches top-k chunks, then `answer` composes the reply.
The Route Ledger records the hop path for audit (`retrieve -> answer`).

## Benchmarks

Published A/B results vs LangGraph baselines (canonical Azure run `mid_20260708_111539`, 100 tasks/scenario):

- Task success + latency + LLM calls: [benchmark/results/BENCHMARK_LATENCY_LLM_SUMMARY.md](https://github.com/insightitsGit/ChorusGraph/blob/master/benchmark/results/BENCHMARK_LATENCY_LLM_SUMMARY.md)
- Full methodology: [docs/BENCHMARK_RESULTS.md](https://github.com/insightitsGit/ChorusGraph/blob/master/docs/BENCHMARK_RESULTS.md)
