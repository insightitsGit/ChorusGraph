"""Chroma vector retrieval with optional PrismRAG taxonomy remap."""

from __future__ import annotations

import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

from chorusgraph.compose.adapters.keyword_retrieval import KeywordRetrievalBackend, _chunk_record
from chorusgraph.embedders import PrismlangOnnxEmbedder

logger = logging.getLogger(__name__)

CategoryFn = Callable[[str], Optional[str]]


def _ensure_prismrag_lib_on_path() -> bool:
    candidates = [
        Path(__file__).resolve().parents[3].parent / "PrismRagLib",
        Path(r"C:\code\PrismRagLib"),
    ]
    for root in candidates:
        if (root / "prismrag_patch" / "mapping.py").is_file():
            path = str(root)
            if path not in sys.path:
                sys.path.insert(0, path)
            return True
    return False


def _create_prismrag_patch(
    *,
    license_key: str,
    mapping: Dict[str, Any],
    alpha: float,
    adapter: str,
) -> Any:
    """Instantiate ``PrismRAGPatch`` after verifying constructor signature."""
    _ensure_prismrag_lib_on_path()
    try:
        from prismrag_patch import PrismRAGPatch
    except ImportError:
        return None
    sig = inspect.signature(PrismRAGPatch.__init__)
    params = list(sig.parameters.keys())
    if "mapping" not in params:
        logger.warning("PrismRAGPatch signature missing mapping param — skipping remap")
        return None
    return PrismRAGPatch(
        license_key=license_key,
        mapping=mapping,
        alpha=alpha,
        adapter=adapter,
    )


class PrismRAGRetrievalBackend:
    """
    Vector search (Chroma) with optional PrismRAG taxonomy-aware re-embedding.

    When ``chromadb`` is unavailable, delegates to an internal ``KeywordRetrievalBackend``.
    Without ``PRISMRAG_LICENSE_KEY``, vector search still runs but taxonomy remap is disabled.
    """

    name = "prismrag"
    _chorusgraph_retrieval_backend = True

    def __init__(
        self,
        *,
        embedder: Any = None,
        mapping: Optional[Dict[str, Any]] = None,
        license_key: Optional[str] = None,
        alpha: float = 0.25,
        collection_name: str = "chorusgraph_retrieval",
        category_fn: Optional[CategoryFn] = None,
    ) -> None:
        self._embedder = embedder or PrismlangOnnxEmbedder()
        self._mapping = dict(mapping or {})
        self._category_fn = category_fn
        self._collection_name = collection_name
        self._alpha = alpha
        self._fallback = KeywordRetrievalBackend()
        self._collection: Any = None
        self._adapter: Any = None
        self._corpus: List[Dict[str, Any]] = []
        self._loaded = False
        self._use_vector = False
        self._use_remap = False

        try:
            import chromadb  # noqa: F401
        except ImportError:
            logger.warning(
                "chromadb not installed — pip install chorusgraph[retrieval]; using keyword retrieval"
            )
            return

        key = (license_key if license_key is not None else os.environ.get("PRISMRAG_LICENSE_KEY", "")).strip()
        patch = None
        if key:
            patch = _create_prismrag_patch(
                license_key=key,
                mapping=self._mapping,
                alpha=self._alpha,
                adapter="chroma",
            )
            if patch is None:
                logger.warning("PrismRAGPatch unavailable — vector search without taxonomy remap")
        else:
            logger.warning("no PRISMRAG_LICENSE_KEY — vector search without taxonomy remap")

        import chromadb

        client = chromadb.Client()
        self._collection = client.get_or_create_collection(collection_name)
        if patch is not None:
            try:
                from prismrag_patch.adapters.chroma import ChromaAdapter

                sig = inspect.signature(ChromaAdapter.__init__)
                if len(sig.parameters) >= 3:
                    self._adapter = ChromaAdapter(patch, self._collection)
                    self._use_remap = True
            except ImportError:
                logger.warning("prismrag_patch ChromaAdapter unavailable — raw Chroma query")
        self._use_vector = True

    def _assign_category(self, text: str, doc: Dict[str, Any]) -> str:
        if self._category_fn is not None:
            cat = self._category_fn(text)
            if cat:
                return cat
        return str(doc.get("category_slug") or doc.get("topic") or "general")

    def index(self, corpus: Sequence[Dict[str, Any]]) -> None:
        self._corpus = [dict(c) for c in corpus]
        self._fallback.index(corpus)
        if not self._use_vector or self._collection is None:
            return

        ids: List[str] = []
        documents: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[Dict[str, str]] = []
        for doc in self._corpus:
            text = str(doc["text"])
            vec = self._embedder.embed(text).astype(np.float32).tolist()
            cat = self._assign_category(text, doc)
            ids.append(str(doc["id"]))
            documents.append(text)
            embeddings.append(vec)
            metadatas.append(
                {
                    "topic": str(doc.get("topic", "")),
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

    def retrieve(self, topic: str, query: str, *, top_k: int = 6) -> List[Dict[str, Any]]:
        if not self._use_vector or self._collection is None:
            return self._fallback.retrieve(topic, query, top_k=top_k)
        if not self._corpus:
            return []
        if not self._loaded:
            self.index(self._corpus)

        qtext = f"{topic} {query}".strip()
        qvec = self._embedder.embed(qtext).astype(np.float32).tolist()
        n_results = min(top_k, len(self._corpus))
        if self._adapter is not None:
            raw = self._adapter.query(
                query_texts=[qtext],
                query_embeddings=[qvec],
                n_results=n_results,
            )
        else:
            raw = self._collection.query(
                query_embeddings=[qvec],
                n_results=n_results,
                include=["documents", "distances", "metadatas"],
            )

        ids = (raw.get("ids") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        docs = (raw.get("documents") or [[]])[0]

        by_id = {str(g["id"]): g for g in self._corpus}
        out: List[Dict[str, Any]] = []
        for idx, doc_id in enumerate(ids):
            base = dict(
                by_id.get(
                    str(doc_id),
                    {"id": doc_id, "topic": topic, "text": docs[idx] if idx < len(docs) else ""},
                )
            )
            dist = float(distances[idx]) if idx < len(distances) else 1.0
            score = 1.0 / (1.0 + dist)
            meta = metas[idx] if idx < len(metas) else {}
            cat = (meta or {}).get("category_slug") or self._assign_category(qtext, base)
            chunk = _chunk_record(base, score=score)
            chunk["category_slug"] = cat
            chunk["prismrag_category"] = cat
            out.append(chunk)
        return out or [_chunk_record(self._corpus[-1])]
