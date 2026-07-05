"""Durable prism_memory factory with SqliteGraphStore (E5)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional


def create_durable_prism_memory(
    *,
    tenant_id: str,
    cache_dir: str | Path,
    model: Optional[str] = None,
    k: int = 8,
    graph_db: str | Path | None = None,
) -> Any:
    """
    Build prismcortex Memory with a durable SqliteGraphStore instead of InMemoryGraphStore.

    Requires prismcortex[prism,gemini] and GEMINI_API_KEY for digest/extract paths.
    """
    from chorusgraph.examples.finance_agent.gemini_client import resolve_gemini_api_key
    from chorusgraph.memory.cortex_compat import apply_cortex_compat_patches
    from chorusgraph.persistence.sqlite_graph_store import SqliteGraphStore

    apply_cortex_compat_patches()
    resolve_gemini_api_key()

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    graph_path = Path(graph_db) if graph_db else cache_path / "graph_store.db"

    from prismcortex.adapters.prism import (
        PrismLangProjector,
        PrismLibCache,
        PrismResonanceAdapter,
    )
    from prismcortex.adapters.reference import InProcessMesh, ListStaging
    from prismcortex.engine import Memory
    from prismcortex.llm.gemini import GeminiClient

    store = SqliteGraphStore(graph_path, tenant_id=tenant_id)
    projector = PrismLangProjector(tenant_id=tenant_id)
    resonance = PrismResonanceAdapter(
        embedding_dim=projector.dim,
        state_path=str(cache_path / "resonance_state.db"),
        onnx_path=str(cache_path / "resonance_engine.onnx"),
    )
    cache = PrismLibCache(db_path=str(cache_path / "prismlib.db"))
    gemini = GeminiClient(model=model)
    return Memory(
        projector=projector,
        extractor=gemini,
        renderer=gemini,
        store=store,
        resonance=resonance,
        cache=cache,
        mesh=InProcessMesh(),
        staging=ListStaging(),
        k=k,
    )


def graph_db_path(cache_dir: str | Path) -> Path:
    return Path(cache_dir) / "graph_store.db"
