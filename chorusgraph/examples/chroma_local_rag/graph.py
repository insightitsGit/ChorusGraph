"""Native ChorusGraph retrieve -> answer pipeline for local Chroma RAG."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from chorusgraph.compose import ChorusStack, PrismRAGRetrievalBackend
from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import dict_node_adapter
from chorusgraph.embedders import PrismlangOnnxEmbedder

TENANT_ID = "chroma-local-rag"
GRAPH_ID = "chroma-local-rag"
TOPIC = "faq"

_SAMPLE_PATH = Path(__file__).resolve().parent / "sample_docs.txt"


def load_corpus(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load FAQ paragraphs from sample_docs.txt into PrismRAG index records."""
    doc_path = path or _SAMPLE_PATH
    blocks = [b.strip() for b in doc_path.read_text(encoding="utf-8").split("\n\n") if b.strip()]
    return [
        {
            "id": str(i),
            "topic": TOPIC,
            "text": block,
            "source": doc_path.name,
        }
        for i, block in enumerate(blocks, start=1)
    ]


def build_retrieval_backend(
    corpus: List[Dict[str, Any]],
    *,
    collection_name: str = "chorusgraph_chroma_local_rag",
) -> PrismRAGRetrievalBackend:
    backend = PrismRAGRetrievalBackend(
        embedder=PrismlangOnnxEmbedder(),
        collection_name=collection_name,
    )
    backend.index(corpus)
    return backend


def _template_answer(chunks: List[str]) -> str:
    body = chunks[0] if chunks else "No matching documents found."
    return f"Based on the documents: {body}"


def _try_gemini_answer(question: str, context: str) -> Optional[str]:
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        return None
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return None

    model = (os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash").split("@", 1)[0]
    prompt = (
        "Answer the question using only the context below. Be concise.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    client = genai.Client(api_key=key)
    cfg = types.GenerateContentConfig(temperature=0.2, max_output_tokens=512)
    response = client.models.generate_content(model=model, contents=prompt, config=cfg)
    text = (response.text or "").strip()
    return text or None


def make_answer_handler():
    def answer(state: Dict[str, Any]) -> Dict[str, Any]:
        question = str(state.get("message") or state.get("query") or "")
        chunks = state.get("kb_context") or state.get("retrieved") or []
        texts = [str(c.get("text") or c.get("content") or "") for c in chunks if c]
        context = "\n".join(t for t in texts if t.strip())
        gemini = _try_gemini_answer(question, context)
        if gemini:
            return {"response": gemini, "rule_chain": ["answer=gemini"]}
        return {"response": _template_answer(texts), "rule_chain": ["answer=template"]}

    return answer


def build_rag_graph(stack: ChorusStack):
    graph = Graph(tenant_id=TENANT_ID, graph_id=GRAPH_ID)
    retrieve = stack.to_retrieve_handler(topic=TOPIC, top_k=3)
    graph.add_node("retrieve", dict_node_adapter(retrieve, hop="retrieve"))
    graph.add_node("answer", dict_node_adapter(make_answer_handler(), hop="answer"))
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)
    return graph.compile(stack=stack)
