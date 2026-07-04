"""Vector-indexed clinical KB — Chroma + optional PrismRAG remap (L2 retrieval)."""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

import numpy as np

from benchmark.healthcare.kb import GUIDELINES
from benchmark.healthcare.prismrag_mapping import assign_clinical_category, try_create_prismrag_patch
from chorusgraph.embedders import PrismlangOnnxEmbedder

_store_lock = threading.Lock()
_store: Optional["GuidelineVectorStore"] = None


def _guideline_record(
    doc: Dict[str, Any],
    *,
    score: float = 0.0,
    category_slug: Optional[str] = None,
) -> Dict[str, Any]:
    slug = category_slug or assign_clinical_category(doc.get("text") or "") or str(doc.get("topic") or "")
    return {
        "id": doc["id"],
        "topic": doc["topic"],
        "text": doc["text"],
        "source": doc.get("source", ""),
        "category_slug": slug,
        "prismrag_category": slug,
        "score": score,
    }


class GuidelineVectorStore:
    """In-process Chroma collection over ``GUIDELINES`` — real nearest-neighbor search."""

    def __init__(
        self,
        *,
        collection: Any,
        adapter: Any = None,
        embedder: Optional[PrismlangOnnxEmbedder] = None,
        use_prismrag_remap: bool = False,
    ) -> None:
        self._collection = collection
        self._adapter = adapter
        self._embedder = embedder or PrismlangOnnxEmbedder()
        self._use_prismrag = use_prismrag_remap
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        ids: List[str] = []
        documents: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[Dict[str, str]] = []
        for doc in GUIDELINES:
            text = str(doc["text"])
            vec = self._embedder.embed(text).astype(np.float32).tolist()
            cat = assign_clinical_category(text) or str(doc["topic"])
            ids.append(str(doc["id"]))
            documents.append(text)
            embeddings.append(vec)
            metadatas.append(
                {
                    "topic": str(doc["topic"]),
                    "source": str(doc.get("source") or ""),
                    "id": str(doc["id"]),
                    "category_slug": cat,
                }
            )
        if self._adapter is not None:
            self._adapter.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        else:
            self._collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        self._loaded = True

    def query(self, topic: str, query: str, *, top_k: int = 6) -> List[Dict[str, Any]]:
        self.load()
        qtext = f"{topic} {query}".strip()
        qvec = self._embedder.embed(qtext).astype(np.float32).tolist()
        if self._adapter is not None:
            raw = self._adapter.query(
                query_texts=[qtext],
                query_embeddings=[qvec],
                n_results=min(top_k, len(GUIDELINES)),
            )
        else:
            raw = self._collection.query(
                query_embeddings=[qvec],
                n_results=min(top_k, len(GUIDELINES)),
                include=["documents", "distances", "metadatas"],
            )

        ids = (raw.get("ids") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        docs = (raw.get("documents") or [[]])[0]

        by_id = {str(g["id"]): g for g in GUIDELINES}
        out: List[Dict[str, Any]] = []
        for idx, doc_id in enumerate(ids):
            base = dict(by_id.get(str(doc_id), {"id": doc_id, "topic": topic, "text": docs[idx] if idx < len(docs) else ""}))
            dist = float(distances[idx]) if idx < len(distances) else 1.0
            score = 1.0 / (1.0 + dist)
            meta = metas[idx] if idx < len(metas) else {}
            cat = (meta or {}).get("category_slug") or assign_clinical_category(qtext)
            out.append(_guideline_record(base, score=score, category_slug=cat))
        return out or [_guideline_record(GUIDELINES[-1])]


def get_guideline_vector_store(*, force_reload: bool = False) -> GuidelineVectorStore:
    """Process-global store — Chroma in-memory; PrismRAG remap when licensed."""
    global _store
    with _store_lock:
        if _store is not None and not force_reload:
            return _store

        import chromadb

        client = chromadb.Client()
        collection = client.get_or_create_collection("chorusgraph_clinical_guidelines")
        patch = try_create_prismrag_patch(adapter="chroma")
        adapter = None
        use_remap = False
        if patch is not None:
            from prismrag_patch.adapters.chroma import ChromaAdapter

            adapter = ChromaAdapter(patch, collection)
            use_remap = True

        _store = GuidelineVectorStore(
            collection=collection,
            adapter=adapter,
            use_prismrag_remap=use_remap,
        )
        _store.load()
        return _store


def retrieve_guidelines_vector(topic: str, query: str, *, top_k: int = 6) -> List[Dict[str, Any]]:
    """Real vector retrieval — drop-in shape for ``retrieve_guidelines`` consumers."""
    return get_guideline_vector_store().query(topic, query, top_k=top_k)


__all__ = [
    "GuidelineVectorStore",
    "get_guideline_vector_store",
    "retrieve_guidelines_vector",
]
