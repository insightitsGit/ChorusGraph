"""Tests for Prism transport spine and envelope handoffs."""

from __future__ import annotations

import numpy as np

from chorusgraph.nodes.retrieve import resonance_rerank
from chorusgraph.transport import (
    InProcSpine,
    PrismAPISpine,
    TransportMode,
    publish_hop,
    resolve_envelope_artifact,
)
from chorusgraph.transport.chorus import ChorusSpine
from chorusgraph.transport.context import PrismEngineContext
from chorusgraph.transport.spine import TransportSpine


def test_inproc_publish_and_resolve():
    ctx = PrismEngineContext(tenant_id="transport-test", enable_cortex=False)
    spine = InProcSpine(cache=ctx.cache, artifact_store=ctx.artifact_store())
    state = {"raw_embedding_384": [0.1] * 384}
    update = spine.publish(hop="intake", artifact={"facts": ["a"]}, state=state)
    assert update.get("latest_envelope_id")
    assert update.get("prism_sequence")
    merged = {**state, **update}
    resolved = spine.resolve(merged)
    assert resolved.get("facts") == ["a"]


def test_chorus_spine_records_frames():
    spine = ChorusSpine(tenant_id="t1")
    frame = spine.encode_frame(
        envelope_id="env-1",
        vector_64=[0.0] * 64,
        hop="writer",
        artifact_ref="env-1",
    )
    out = spine.deliver(frame, from_hop="researcher", to_hop="writer")
    assert out["last_transport"] == TransportMode.CHORUS_LOCAL.value
    assert len(spine._sent) == 1


def test_prismapi_spine_stub():
    api = PrismAPISpine(tenant_id="consumer")
    resp = api.invoke(provider_id="legal-kb", query_text="contract clause")
    assert resp.provider_id == "legal-kb"
    assert api._calls[0].query_text == "contract clause"
    state = api.to_state_update(resp)
    assert state["last_transport"] == TransportMode.CHORUS_FEDERATED.value


def test_graph_edge_transport_metadata():
    ctx = PrismEngineContext(tenant_id="edge-test", enable_cortex=False)
    spine = TransportSpine(ctx)
    state = {"latest_envelope_id": "env-1", "query_vector_64": [0.1] * 64}
    result = spine.edge_handoff(
        mode=TransportMode.INPROC,
        from_hop="a",
        to_hop="b",
        state=state,
    )
    assert result["last_transport"] == "inproc"
    assert result["last_edge"] == "a->b"


def test_resonance_rerank_orders_by_score():
    ctx = PrismEngineContext(tenant_id="rerank-test", enable_cortex=False)
    chunks = [
        {"text": "alpha document", "id": "1"},
        {"text": "beta document", "id": "2"},
    ]
    raw = ctx.cache._embedder.embed("alpha")
    env = ctx.cache._projector.project(raw)
    ranked = resonance_rerank(
        ctx.cache,
        query_vector_64=np.asarray(env.vector, dtype=np.float32),
        chunks=chunks,
        top_k=2,
    )
    assert len(ranked) == 2
    assert "resonance_score" in ranked[0]
    assert ranked[0]["resonance_score"] >= ranked[1]["resonance_score"]
