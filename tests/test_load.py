"""E7 load/throughput tests."""

from __future__ import annotations

from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import NodeContext
from chorusgraph.core.channels import NodeUpdate
from benchmark.load.harness import run_load, run_sweep


def _compiled():
    def inc(ctx: NodeContext) -> NodeUpdate:
        v = int(ctx.read().get("n") or 0) + 1
        return ctx.publish(artifact={"n": v}, category_slug="general")

    g = Graph(graph_id="load-test")
    g.add_node("inc", inc)
    g.add_edge(START, "inc")
    g.add_edge("inc", END)
    return g.compile()


def test_load_harness_reports_throughput():
    compiled = _compiled()
    report = run_load(lambda: compiled.invoke({"n": 0}), total_requests=20, concurrency=4)
    assert report.total_requests == 20
    assert report.throughput_rps > 0
    assert report.success_rate == 1.0
    assert report.latency_p50_ms >= 0


def test_load_sweep_increasing_concurrency():
    compiled = _compiled()
    reports = run_sweep(lambda: compiled.invoke({"n": 0}), concurrencies=[1, 2], requests_per_level=10)
    assert len(reports) == 2
    assert all(r.success_rate == 1.0 for r in reports)
