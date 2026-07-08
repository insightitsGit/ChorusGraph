"""Run local Chroma + ChorusGraph RAG demo (no API key required)."""

from __future__ import annotations

import sys

from chorusgraph import SqliteLedgerSink, wrap
from chorusgraph.compose import ChorusStack

from chorusgraph.examples.chroma_local_rag.graph import (
    GRAPH_ID,
    TENANT_ID,
    build_rag_graph,
    build_retrieval_backend,
    load_corpus,
)


def _snippet(text: str, max_len: int = 100) -> str:
    flat = " ".join(text.split())
    if len(flat) <= max_len:
        return flat
    return flat[: max_len - 3] + "..."


def run_demo(*, query: str = "What is the refund policy?") -> dict:
    corpus = load_corpus()
    backend = build_retrieval_backend(corpus)
    stack = ChorusStack.defaults(tenant_id=TENANT_ID).with_retrieval(backend)
    compiled = build_rag_graph(stack)

    sink = SqliteLedgerSink(":memory:")
    wrapped = wrap(compiled, tenant_id=TENANT_ID, graph_id=GRAPH_ID, sink=sink)
    result = wrapped.invoke(
        {
            "tenant_id": TENANT_ID,
            "message": query,
            "topic": "faq",
            "rule_chain": [],
        }
    )
    path = [s.node for s in wrapped.last_ledger.steps] if wrapped.last_ledger else []
    chunks = result.get("kb_context") or result.get("retrieved") or []
    return {"query": query, "chunks": chunks, "response": result.get("response", ""), "path": path}


def main() -> None:
    try:
        out = run_demo()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print("Query:", out["query"])
    print("\nRetrieved chunks:")
    for i, chunk in enumerate(out["chunks"][:3], start=1):
        text = str(chunk.get("text") or chunk.get("content") or "")
        score = chunk.get("score") or chunk.get("resonance_score")
        score_txt = f" (score={score:.3f})" if isinstance(score, (int, float)) else ""
        print(f"  {i}. {_snippet(text)}{score_txt}")

    print("\nAnswer:")
    print(out["response"])
    print("\nLedger path:", " -> ".join(out["path"]))


if __name__ == "__main__":
    main()
