"""Chroma vector retrieval with optional PrismRAG taxonomy remap."""

from __future__ import annotations

import inspect
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

from chorusgraph.compose.adapters.keyword_retrieval import KeywordRetrievalBackend, _chunk_record
from chorusgraph.compose.retrieval_stats import RetrievalStats
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


def _project_64(raw_384: np.ndarray, *, tenant_id: str, projector_cache: Any = None) -> List[float]:
    """Project 384-d embed to tenant-seeded 64-d via PrismCache projector."""
    cache = projector_cache
    if cache is None:
        from prism.cache import PrismCache

        cache = PrismCache.build(tenant_id=tenant_id)
    env = cache._projector.project(np.asarray(raw_384, dtype=np.float32).ravel())
    return np.asarray(env.vector, dtype=np.float32).ravel().tolist()


class PrismRAGRetrievalBackend:
    """
    Vector search (Chroma) with optional PrismRAG taxonomy-aware re-embedding.

    When ``chromadb`` is unavailable, delegates to an internal ``KeywordRetrievalBackend``.
    Without ``PRISMRAG_LICENSE_KEY``, vector search still runs but taxonomy remap is disabled.

    Optional warm chunk vectors: ``index(..., partition=, version=)`` stores ``vector_64``
    per chunk; ``retrieve`` attaches them; ``warm`` / ``is_ready`` / ``stats`` support
    process-boot readiness without re-encoding on every query.
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
        tenant_id: str = "default",
    ) -> None:
        self._embedder = embedder or PrismlangOnnxEmbedder()
        self._mapping = dict(mapping or {})
        self._category_fn = category_fn
        self._collection_name = collection_name
        self._alpha = alpha
        self._tenant_id = tenant_id
        self._fallback = KeywordRetrievalBackend()
        self._collections: Dict[str, Any] = {}
        self._adapters: Dict[str, Any] = {}
        self._patch: Any = None
        self._partitions: Dict[str, List[Dict[str, Any]]] = {}
        self._versions: Dict[str, Optional[str]] = {}
        self._loaded: Dict[str, bool] = {}
        self._vector_64: Dict[str, Dict[str, List[float]]] = {}
        self._stats = RetrievalStats()
        self._use_vector = False
        self._use_remap = False
        # Legacy single-corpus mirror
        self._corpus: List[Dict[str, Any]] = []
        self._collection: Any = None
        self._adapter: Any = None
        self._loaded_flag = False
        self._projector_cache: Any = None

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

        self._patch = patch
        self._use_remap = patch is not None
        self._use_vector = True
        # Default partition collection (legacy attribute)
        self._collection = self._get_or_create_collection("default")
        if self._use_remap:
            self._adapter = self._adapters.get("default")
        try:
            from prism.cache import PrismCache

            self._projector_cache = PrismCache.build(tenant_id=self._tenant_id, embedder=self._embedder)
        except Exception as exc:
            logger.warning("PrismCache projector unavailable for vector_64: %s", exc)

    def _assign_category(self, text: str, doc: Dict[str, Any]) -> str:
        if self._category_fn is not None:
            cat = self._category_fn(text)
            if cat:
                return cat
        return str(doc.get("category_slug") or doc.get("topic") or "general")

    def _collection_name_for(self, partition: str) -> str:
        if partition == "default":
            return self._collection_name
        return f"{self._collection_name}__{partition}"

    def _get_or_create_collection(self, partition: str) -> Any:
        if partition in self._collections:
            return self._collections[partition]
        import chromadb

        client = chromadb.Client()
        coll = client.get_or_create_collection(self._collection_name_for(partition))
        self._collections[partition] = coll
        if self._patch is not None:
            try:
                from prismrag_patch.adapters.chroma import ChromaAdapter

                sig = inspect.signature(ChromaAdapter.__init__)
                if len(sig.parameters) >= 3:
                    self._adapters[partition] = ChromaAdapter(self._patch, coll)
            except ImportError:
                logger.warning("prismrag_patch ChromaAdapter unavailable — raw Chroma query")
        return coll

    def index(
        self,
        corpus: Sequence[Dict[str, Any]],
        *,
        partition: str = "default",
        version: Optional[str] = None,
    ) -> None:
        rows = [dict(c) for c in corpus]
        self._partitions[partition] = rows
        if partition == "default":
            self._corpus = rows
        self._fallback.index(rows, partition=partition, version=version)

        if (
            version is not None
            and self._loaded.get(partition)
            and self._versions.get(partition) == version
        ):
            return

        self._versions[partition] = version
        self._stats.partition_versions[partition] = version
        self._vector_64[partition] = {}

        if not self._use_vector:
            self._loaded[partition] = bool(rows)
            self._loaded_flag = self._loaded.get("default", False)
            self._stats.ready_partitions = tuple(p for p, ok in self._loaded.items() if ok)
            return

        collection = self._get_or_create_collection(partition)
        adapter = self._adapters.get(partition)

        ids: List[str] = []
        documents: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[Dict[str, str]] = []
        for doc in rows:
            text = str(doc["text"])
            raw = self._embedder.embed(text).astype(np.float32)
            self._stats.corpus_embeds += 1
            vec = raw.tolist()
            vec64 = _project_64(
                raw,
                tenant_id=self._tenant_id,
                projector_cache=self._projector_cache,
            )
            self._vector_64[partition][str(doc["id"])] = vec64
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
                    "partition": partition,
                }
            )

        # Replace partition contents: delete existing ids then add
        try:
            existing = collection.get()
            old_ids = list(existing.get("ids") or [])
            if old_ids:
                collection.delete(ids=old_ids)
        except Exception:
            pass

        if not ids:
            self._loaded[partition] = False
            return

        if adapter is not None:
            adapter.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        else:
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        self._loaded[partition] = True
        if partition == "default":
            self._collection = collection
            self._adapter = adapter
            self._loaded_flag = True
        self._stats.ready_partitions = tuple(p for p, ok in self._loaded.items() if ok)

    def retrieve(
        self,
        topic: str,
        query: str,
        *,
        top_k: int = 6,
        partition: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        part = partition or "default"
        if not self._use_vector:
            return self._fallback.retrieve(topic, query, top_k=top_k, partition=part)

        corpus = self._partitions.get(part) or (self._corpus if part == "default" else [])
        if not corpus:
            return []

        if not self._loaded.get(part):
            self.index(corpus, partition=part, version=self._versions.get(part))

        collection = self._collections.get(part) or self._get_or_create_collection(part)
        adapter = self._adapters.get(part)

        qtext = f"{topic} {query}".strip()
        qvec = self._embedder.embed(qtext).astype(np.float32).tolist()
        self._stats.query_embeds += 1
        n_results = min(top_k, len(corpus))
        if adapter is not None:
            raw = adapter.query(
                query_texts=[qtext],
                query_embeddings=[qvec],
                n_results=n_results,
            )
        else:
            raw = collection.query(
                query_embeddings=[qvec],
                n_results=n_results,
                include=["documents", "distances", "metadatas"],
            )

        ids = (raw.get("ids") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        docs = (raw.get("documents") or [[]])[0]
        vec_map = self._vector_64.get(part) or {}

        by_id = {str(g["id"]): g for g in corpus}
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
            v64 = vec_map.get(str(doc_id))
            if v64 is not None:
                chunk["vector_64"] = list(v64)
            out.append(chunk)
        if out:
            return out
        fallback = _chunk_record(corpus[-1])
        v64 = vec_map.get(str(corpus[-1]["id"]))
        if v64 is not None:
            fallback["vector_64"] = list(v64)
        return [fallback]

    def warm(self, *, partition: Optional[str] = None) -> None:
        t0 = time.perf_counter()
        if partition is not None:
            parts = [partition]
        else:
            parts = list(self._partitions.keys()) or ["default"]
        for part in parts:
            rows = self._partitions.get(part) or []
            if not rows:
                self._loaded[part] = False
                continue
            if self._loaded.get(part):
                continue
            self.index(rows, partition=part, version=self._versions.get(part))
        self._stats.ready_partitions = tuple(p for p, ok in self._loaded.items() if ok)
        self._stats.last_warm_ms = (time.perf_counter() - t0) * 1000.0
        self._fallback.warm(partition=partition)

    def is_ready(self, *, partition: Optional[str] = None) -> bool:
        if not self._use_vector:
            return self._fallback.is_ready(partition=partition)
        if partition is not None:
            return bool(self._loaded.get(partition))
        if not self._partitions:
            return bool(self._loaded_flag or self._loaded.get("default"))
        return all(self._loaded.get(p) for p in self._partitions)

    def stats(self) -> RetrievalStats:
        return self._stats
