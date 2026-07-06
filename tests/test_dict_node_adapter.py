"""Tests for dict_node_adapter — Bug-2 resonance slug collision fix."""

from __future__ import annotations

from chorusgraph.core.bus import frequency_for_slug
from chorusgraph.core.channels import ChannelState
from chorusgraph.core.node import NodeContext, dict_node_adapter


def _ctx_for(hop: str, *, route: str = "site_kb") -> NodeContext:
    from chorusgraph.core.bus import ResonanceBus

    bus = ResonanceBus()
    bus.register_node(hop, category_slug=hop)
    state = ChannelState.from_input({"route": route})
    return NodeContext(
        state=state.snapshot(),
        node_id=hop,
        super_step=0,
        bus=bus,
        projector=None,
    )


def test_dict_node_adapter_hop_slug_avoids_shared_route_collision():
    """Two nodes carrying the same router `route` must not share a Resonance slug."""
    shared_route = "site_kb"
    node_a = dict_node_adapter(
        lambda s: {"route": shared_route, "output": "a"},
        hop="fetch_docs",
    )
    node_b = dict_node_adapter(
        lambda s: {"route": shared_route, "output": "b"},
        hop="summarize",
    )

    update_a = node_a(_ctx_for("fetch_docs", route=shared_route))
    update_b = node_b(_ctx_for("summarize", route=shared_route))

    slug_a = str(update_a.primary["category_slug"])
    slug_b = str(update_b.primary["category_slug"])

    assert slug_a == "fetch_docs"
    assert slug_b == "summarize"
    assert slug_a != slug_b
    assert frequency_for_slug(slug_a) != frequency_for_slug(slug_b)


def test_dict_node_adapter_explicit_category_slug_wins():
    node = dict_node_adapter(
        lambda s: {"route": "site_kb", "category_slug": "custom_topic"},
        hop="worker",
    )
    update = node(_ctx_for("worker"))
    assert update.primary["category_slug"] == "custom_topic"


def test_dict_node_adapter_category_slug_from_route_legacy():
    node = dict_node_adapter(
        lambda s: {"route": "site_kb", "output": "x"},
        hop="worker",
        category_slug_from="route",
    )
    update = node(_ctx_for("worker"))
    assert update.primary["category_slug"] == "site_kb"
