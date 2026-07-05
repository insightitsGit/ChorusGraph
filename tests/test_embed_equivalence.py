"""H12 — deterministic equivalence: precomputed raw_384 matches full embed path."""

from __future__ import annotations

import numpy as np

from chorusgraph.cache_gate import gate, seed_cache_entry
from chorusgraph.policy.embedder_guard import build_guarded_cache
from chorusgraph.sections.models import CachePolicy, Section
from chorusgraph.transforms.projector import project_from_raw, project_text


def test_gate_precomputed_raw_matches_full_embed():
    cache = build_guarded_cache("gate-equiv-test")
    sidecar = __import__("chorusgraph.cache_gate.sidecar", fromlist=["SidecarStore"]).SidecarStore(
        ":memory:"
    )
    query = "USD to EUR exchange rate today"
    seed_cache_entry(
        cache,
        sidecar,
        query=query,
        value={"from_currency": "USD", "to_currency": "EUR", "rate": 0.91, "date": "2026-01-01"},
        category_slug="fx_rates",
        cache_policy="replay_safe",
    )
    section = Section(
        section_id="fx",
        category_slug="fx_rates",
        content=query,
        cache_policy=CachePolicy.REPLAY_SAFE,
    )

    embedder = cache._embedder
    if hasattr(embedder, "reset_turn_calls"):
        embedder.reset_turn_calls()

    d_full = gate(query, section, cache, sidecar, coarse_threshold=0.82, verify_threshold=0.85)

    if hasattr(embedder, "reset_turn_calls"):
        embedder.reset_turn_calls()
    raw, envelope = project_text(cache, query)
    d_shared = gate(
        query,
        section,
        cache,
        sidecar,
        coarse_threshold=0.82,
        verify_threshold=0.85,
        raw_embedding_384=raw,
        projected_vector_64=np.asarray(envelope.vector, dtype=np.float32),
    )

    assert d_full.kind == d_shared.kind
    assert d_full.is_hit == d_shared.is_hit
    if d_full.verify_score is not None and d_shared.verify_score is not None:
        assert abs(d_full.verify_score - d_shared.verify_score) < 1e-6
    assert embedder.turn_calls == 1


def test_project_from_raw_matches_project_text():
    cache = build_guarded_cache("project-equiv-test")
    text = "What is the dollar to euro FX rate?"
    raw_a, env_a = project_text(cache, text)
    raw_b, env_b = project_from_raw(cache, raw_a)
    assert np.allclose(raw_a, raw_b)
    assert list(env_a.vector) == list(env_b.vector)
