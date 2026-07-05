"""H13 — Cortex native 128-d projection from shared raw_384."""

from __future__ import annotations

import numpy as np

from chorusgraph.policy.embedder_guard import build_guarded_cache
from chorusgraph.transforms.cortex_projector import project_cortex_from_raw, project_cortex_text
from chorusgraph.transforms.projector import project_from_raw, project_text


def test_cortex_projection_is_128d():
    slug, vec, chain = project_cortex_text(
        "finance-tenant", "conservative investor low risk tolerance"
    )
    assert len(vec) == 128
    assert slug
    assert any("k=128" in r for r in chain)


def test_cortex_from_raw_matches_full_path():
    text = "What risk profile did I tell you I prefer?"
    tenant = "cortex-equiv-test"
    _, full, _ = project_cortex_text(tenant, text)
    cache = build_guarded_cache("cortex-raw-test")
    raw, _ = project_text(cache, text)
    _, from_raw, _ = project_cortex_from_raw(tenant, text, raw)
    assert full.shape == (128,)
    assert np.allclose(full, from_raw, atol=1e-5)


def test_cache_projection_stays_64d_while_cortex_128d():
    cache = build_guarded_cache("dim-split-test")
    text = "USD to EUR exchange rate"
    _, env64 = project_from_raw(cache, project_text(cache, text)[0])
    _, vec128, _ = project_cortex_from_raw("dim-split-test", text, project_text(cache, text)[0])
    assert len(env64.vector) == 64
    assert len(vec128) == 128
