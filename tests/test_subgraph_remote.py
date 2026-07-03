"""T5 — remote subgraph contract tests."""

from __future__ import annotations

from chorusgraph.core.constants import END, START
from chorusgraph.core.graph import Graph
from chorusgraph.core.node import NodeContext, native_node
from chorusgraph.core.subgraph_transport import decode_boundary_envelope, encode_boundary_envelope


@native_node
def echo(ctx: NodeContext):
    return ctx.publish(artifact={"child_result": ctx.read().get("msg", "")})


def _child():
    g = Graph()
    g.add_node("echo", echo)
    g.add_edge(START, "echo")
    g.add_edge("echo", END)
    return g.compile()


def test_encode_decode_round_trip():
    payload = {"msg": "hi", "vector": [0.1] * 64, "envelope_id": "e1"}
    encoded = encode_boundary_envelope(payload)
    decoded = decode_boundary_envelope(encoded)
    assert decoded.get("msg") == "hi"
    assert len(decoded.get("vector") or []) == 64


def test_chorus_location_round_trip():
    parent = Graph()
    parent.add_subgraph(
        "remote_child",
        _child(),
        input_map={"message": "msg"},
        output_map={"child_result": "child_result"},
        location="chorus",
    )
    parent.add_edge(START, "remote_child")
    parent.add_edge("remote_child", END)
    out = parent.compile().invoke({"message": "chorus"}, config={"configurable": {"thread_id": "remote-chorus"}})
    assert out.get("child_result") == "chorus"


def test_prismapi_location_round_trip():
    parent = Graph()
    parent.add_subgraph(
        "remote_child",
        _child(),
        input_map={"message": "msg"},
        output_map={"child_result": "child_result"},
        location="prismapi",
    )
    parent.add_edge(START, "remote_child")
    parent.add_edge("remote_child", END)
    out = parent.compile().invoke({"message": "api"}, config={"configurable": {"thread_id": "remote-api"}})
    assert out.get("child_result") == "api"
