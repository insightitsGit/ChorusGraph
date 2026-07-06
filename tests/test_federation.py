"""T7 — PrismAPI federation + Send-over-transport tests."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from chorusgraph.core.constants import END, START
from chorusgraph.core.graph import Graph
from chorusgraph.core.node import NodeContext, native_node
from chorusgraph.core.send import Send
from chorusgraph.core.subgraph_transport import build_send_batch_frame, invoke_remote_send_batch
from chorusgraph.core.transport_router import TransportRouter
from chorusgraph.transport.chorus import ChorusSpine
from chorusgraph.transport.modes import TransportMode


class CountingEmbedder:
    def __init__(self) -> None:
        self.call_count = 0

    def embed(self, texts: list[str]) -> np.ndarray:
        self.call_count += 1
        dim = 384
        out = np.zeros((len(texts), dim), dtype=np.float32)
        for i, text in enumerate(texts):
            out[i, 0] = float(len(text))
        return out


def _remote_child_graph():
    @native_node
    def worker(ctx: NodeContext):
        item = ctx.read().get("item", "?")
        return ctx.publish(artifact={"item": item, "processed": True})

    g = Graph()
    g.add_node("worker", worker)
    g.add_edge(START, "worker")
    g.add_edge("worker", END)
    return g.compile()


def _remote_batch_executor(batch: Any, spec: Any, config: dict[str, Any]) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    from chorusgraph.core.subgraph_transport import decode_boundary_envelope

    for idx, ref in enumerate(batch.artifact_refs):
        import json

        payload = json.loads(ref) if ref.startswith("{") else {"item": ref}
        child_input = decode_boundary_envelope(
            {
                "vector_64": batch.vectors[idx],
                "artifact_ref": ref,
                "envelope_id": f"remote-{idx}",
            }
        )
        child_input.update(payload)
        values = spec.child.invoke(child_input, config=config)
        outputs.append(
            {
                "item": values.get("item"),
                "processed": values.get("processed"),
                "branch_id": f"b{idx}",
            }
        )
    return outputs


@native_node
def map_ten(ctx: NodeContext):
    return [Send("remote", {"item": x}) for x in (ctx.read().get("items") or [])]


@native_node
def reduce_quorum(ctx: NodeContext):
    outputs = ctx.read().get("branch_outputs") or []
    return ctx.publish(
        artifact={"count": len(outputs), "items": sorted(o.get("item", "") for o in outputs)}
    )


def test_prismapi_zero_reembed_on_query_vector():
    pytest.importorskip("prism.api")
    from prism.api.consumer import PrismAPIClient
    from prism.api.provider import PrismAPIProvider
    from prism.lib.fabric import CHORUSFrame
    from prism.lib.lang import PrismProjector, ProjectionConfig

    if not hasattr(CHORUSFrame, "from_api_request"):
        pytest.skip("prismlib-plus>=0.7.0 required for CHORUSFrame.from_api_request")

    embedder = CountingEmbedder()
    projector = PrismProjector(ProjectionConfig(tenant_id="fed", target_dim=64))
    provider = PrismAPIProvider(
        projector=projector,
        embedder=embedder,
        semantic_fields=["body"],
        provider_id="test-provider",
    )

    @provider.expose
    def search(query: str, top_k: int = 5) -> list[dict]:
        return [{"id": "1", "body": f"doc for {query}"}]

    client = PrismAPIClient(projector=projector, embedder=embedder, loopback_provider=provider)
    remote_embedder = CountingEmbedder()
    client._embedder = remote_embedder  # consumer-side; should not run on query_vector path

    vec = np.zeros(64, dtype=np.float32)
    client.query_vector(vec, top_k=1)
    assert remote_embedder.call_count == 0


def test_remote_send_batch_one_frame():
    child = _remote_child_graph()
    parent = Graph()
    parent.add_subgraph(
        "remote",
        child,
        input_map={"item": "item"},
        output_map={"processed": "processed", "item": "item"},
        location="chorus",
    )
    from chorusgraph.core.subgraph import SubgraphSpec

    spec = SubgraphSpec(
        name="remote",
        child=child,
        input_map={"item": "item"},
        output_map={"processed": "processed", "item": "item"},
        location="chorus",
    )
    from chorusgraph.core.send import BranchTask, branch_id_for

    tasks = [
        BranchTask(branch_id=branch_id_for("map", 1, i), target="remote", payload={"item": str(i)})
        for i in range(10)
    ]
    router = TransportRouter(
        tenant_id="fed",
        mode=TransportMode.CHORUS_LOCAL,
        chorus=ChorusSpine(tenant_id="fed"),
        remote_batch_handler=_remote_batch_executor,
    )
    batch_frame = build_send_batch_frame(tasks, tenant_id="fed")
    router.deliver_batch(batch_frame, from_hop="map", to_hop="remote")
    assert router.batch_deliveries == 1

    outputs = invoke_remote_send_batch(
        spec,
        tasks,
        config={"configurable": {"thread_id": "fed", "tenant_id": "fed"}},
        transport=router,
        remote_executor=_remote_batch_executor,
    )
    assert len(outputs) == 10


def test_federation_graph_quorum_eight():
    child = _remote_child_graph()
    g = Graph()
    g.add_subgraph(
        "remote",
        child,
        input_map={"item": "item"},
        output_map={"processed": "processed", "item": "item"},
        location="chorus",
    )
    g.add_node("map", map_ten)
    g.add_node("reduce", reduce_quorum, join=("quorum", 8))
    g.add_edge(START, "map")
    g.add_edge("remote", "reduce")
    g.add_edge("reduce", END)

    router = TransportRouter(
        tenant_id="fed-graph",
        mode=TransportMode.CHORUS_LOCAL,
        chorus=ChorusSpine(tenant_id="fed-graph"),
        remote_batch_handler=_remote_batch_executor,
    )
    compiled = g.compile(transport=router)
    out = compiled.invoke(
        {"items": [str(i) for i in range(10)]},
        config={"configurable": {"thread_id": "fed-q8"}},
    )
    assert out["count"] == 8
    assert router.batch_deliveries == 1
    events = compiled.last_tracker.events if compiled.last_tracker else []
    remote_steps = [e for e in events if str(e.get("route_via") or "").startswith("remote_")]
    assert remote_steps
