"""Integration tests for engine phases P2–P7."""

from __future__ import annotations

import tempfile
from pathlib import Path

from chorusgraph import SqliteLedgerSink, get_run, wrap
from chorusgraph.cache_gate import SidecarStore, seed_cache_entry
from chorusgraph.core import END, START, Graph
from chorusgraph.core.cache_interceptor import CacheRuntime
from chorusgraph.core.channels import NodeUpdate
from chorusgraph.core.node import NodeContext
from chorusgraph.core.persistence import json_file_checkpointer
from chorusgraph.core.trace import RouteTracker
from chorusgraph.examples.demo_graph import GRAPH_ID, TENANT_ID, build_demo_graph
from chorusgraph.examples.multi_agent_graph import build_multi_agent_graph
from chorusgraph.policy.embedder_guard import build_guarded_cache
from chorusgraph.sections.models import CachePolicy


def test_p2_checkpoint_resume_after_restart():
    with tempfile.TemporaryDirectory() as tmp:
        cp = json_file_checkpointer(str(Path(tmp) / "cp"))
        config = {"configurable": {"thread_id": "resume-test-1"}}

        visits: list[str] = []

        def a(ctx: NodeContext) -> NodeUpdate:
            visits.append("a")
            return ctx.publish(artifact={"step": "a", "raw_output": "a"}, category_slug="general")

        def b(ctx: NodeContext) -> NodeUpdate:
            visits.append("b")
            return ctx.publish(artifact={"step": "b", "raw_output": "b"}, category_slug="general")

        g = Graph()
        g.add_node("a", a)
        g.add_node("b", b)
        g.set_interrupt_after("a")
        g.add_edge(START, "a")
        g.add_edge("a", "b")
        g.add_edge("b", END)
        compiled = g.compile(checkpointer=cp)

        out1 = compiled.invoke({"seed": 1}, config=config)
        assert out1.get("__interrupt__") is True
        assert visits == ["a"]

        out2 = compiled.invoke(None, config=config)
        assert "__interrupt__" not in out2
        assert visits == ["a", "b"]
        assert out2.get("step") == "b"


def test_p2_get_state_and_history():
    with tempfile.TemporaryDirectory() as tmp:
        cp = json_file_checkpointer(str(Path(tmp) / "cp"))
        config = {"configurable": {"thread_id": "history-1"}}

        def n(ctx: NodeContext) -> NodeUpdate:
            return ctx.publish(artifact={"v": 1}, category_slug="general")

        g = Graph()
        g.add_node("n", n)
        g.add_edge(START, "n")
        g.add_edge("n", END)
        compiled = g.compile(checkpointer=cp)
        compiled.invoke({"x": 1}, config=config)

        snap = compiled.get_state(config)
        assert snap.values.get("x") == 1
        history = compiled.get_state_history(config, limit=5)
        assert len(history) >= 1


def test_p3_stream_modes():
    def n(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"msg": "hi"}, category_slug="general")

    g = Graph()
    g.add_node("n", n)
    g.add_edge(START, "n")
    g.add_edge("n", END)
    compiled = g.compile()

    values = list(compiled.stream({"seed": True}, stream_mode="values"))
    assert values and values[-1].get("msg") == "hi"

    updates = list(compiled.stream({"seed": True}, stream_mode="updates"))
    assert updates and "n" in updates[0]

    debug = list(compiled.stream({"seed": True}, stream_mode="debug"))
    assert any(e.get("type") == "task_result" for e in debug)


def test_p4_cache_skip_zero_llm():
    cache = build_guarded_cache("engine-cache-skip")
    sidecar = SidecarStore(":memory:")
    seed_cache_entry(
        cache,
        sidecar,
        query="hello cache",
        value={"response": "cached answer", "raw_output": "cached answer"},
        category_slug="general",
        cache_policy="exact",
    )
    runtime = CacheRuntime(cache, sidecar, coarse_threshold=0.80, verify_threshold=0.85)
    llm_calls = {"n": 0}

    def expensive(ctx: NodeContext) -> NodeUpdate:
        llm_calls["n"] += 1
        return ctx.publish(artifact={"response": "fresh"}, category_slug="general")

    g = Graph()
    g.add_node("expensive", expensive, cache_policy=CachePolicy.EXACT, cache_query_key="message")
    g.add_edge(START, "expensive")
    g.add_edge("expensive", END)
    compiled = g.compile(cache_runtime=runtime)

    miss = compiled.invoke({"message": "unique query xyz"})
    assert miss["response"] == "fresh"
    assert llm_calls["n"] == 1

    hit = compiled.invoke({"message": "hello cache"})
    assert hit["response"] == "cached answer"
    assert llm_calls["n"] == 1  # no additional LLM call
    assert compiled.last_ledger is not None
    assert compiled.last_ledger.steps[-1].cache_hit is True


def test_p4_native_ledger_via_wrap():
    sink = SqliteLedgerSink(":memory:")
    wrapped = wrap(build_demo_graph(), tenant_id=TENANT_ID, graph_id=GRAPH_ID, sink=sink)
    wrapped.invoke(
        {
            "tenant_id": TENANT_ID,
            "message": "hi",
            "score": 0,
            "route": "",
            "rule_chain": [],
            "prism_sequence": [],
            "response": "",
        }
    )
    assert wrapped.last_ledger is not None
    assert [s.node for s in wrapped.last_ledger.steps] == [
        "analyze",
        "route_decision",
        "short_path",
    ]
    persisted = get_run(sink, wrapped.last_ledger.run_id)
    assert persisted is not None


def test_p4_multi_agent_role_graph():
    sink = SqliteLedgerSink(":memory:")
    compiled = build_multi_agent_graph()
    wrapped = wrap(
        compiled, tenant_id="multi-agent-demo", graph_id="researcher-writer-validator", sink=sink
    )
    out = wrapped.invoke({"message": "Explain ChorusGraph engine"})
    assert out.get("response")
    nodes = [s.node for s in wrapped.last_ledger.steps]
    assert nodes == ["researcher", "writer", "validator"]


def test_route_tracker_events():
    tracker = RouteTracker(tenant_id="t", graph_id="g", sink=SqliteLedgerSink(":memory:"))
    tracker.record_super_step(0, ["a"])
    tracker.record_step(node="a", edge_taken="b", rule_chain=["route=b"], duration_ms=5)
    tracker.flush()
    assert len(tracker.events) >= 2
    assert tracker.ledger.steps[0].node == "a"


def test_p5_transport_router_chorus():
    from chorusgraph.core.transport_router import TransportRouter

    router = TransportRouter.for_agents("tenant", local=False, same_cluster=True)
    result = router.deliver_envelope(
        envelope_id="e1",
        vector_64=[0.1] * 64,
        hop="a",
        artifact_ref="e1",
        from_hop="a",
        to_hop="b",
    )
    assert "chorus_frame_id" in result or result.get("last_transport") == "chorus_local"


def test_checkpoint_no_langgraph_in_chorusgraph_checkpoint():
    import chorusgraph.checkpoint.prism as mod

    source = Path(mod.__file__).read_text(encoding="utf-8").lower()
    assert "from langgraph" not in source
    assert "import langgraph" not in source


def test_p2_update_state_forks_checkpoint_chain():
    with tempfile.TemporaryDirectory() as tmp:
        cp = json_file_checkpointer(str(Path(tmp) / "cp"))
        config = {"configurable": {"thread_id": "fork-test-1"}}

        def n(ctx: NodeContext) -> NodeUpdate:
            return ctx.publish(artifact={"v": 1}, category_slug="general")

        g = Graph()
        g.add_node("n", n)
        g.add_edge(START, "n")
        g.add_edge("n", END)
        compiled = g.compile(checkpointer=cp)
        compiled.invoke({"x": 1}, config=config)

        snap = compiled.update_state(config, {"forked": True})
        assert snap.values.get("forked") is True
        assert snap.parent_config is not None
        history = compiled.get_state_history(snap.config, limit=5)
        assert len(history) >= 2


def test_p3_live_stream_yields_before_next_node():
    b_started_after_a_event: list[bool] = []

    def node_a(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"from": "a"}, category_slug="general")

    def node_b(ctx: NodeContext) -> NodeUpdate:
        b_started_after_a_event.append(True)
        return ctx.publish(artifact={"from": "b"}, category_slug="general")

    g = Graph()
    g.add_node("a", node_a)
    g.add_node("b", node_b)
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", END)
    compiled = g.compile()

    saw_a = False
    for event in compiled.stream({}, stream_mode="updates"):
        if "a" in event:
            saw_a = True
        if "b" in event:
            assert saw_a, "node b event must not arrive before node a event"
            b_started_after_a_event.clear()
    assert saw_a


def test_p3_interrupt_mid_stream():
    with tempfile.TemporaryDirectory() as tmp:
        cp = json_file_checkpointer(str(Path(tmp) / "cp"))
        config = {"configurable": {"thread_id": "stream-interrupt-1"}}

        def a(ctx: NodeContext) -> NodeUpdate:
            return ctx.publish(artifact={"step": "a"}, category_slug="general")

        def b(ctx: NodeContext) -> NodeUpdate:
            return ctx.publish(artifact={"step": "b"}, category_slug="general")

        g = Graph()
        g.add_node("a", a)
        g.add_node("b", b)
        g.set_interrupt_after("a")
        g.add_edge(START, "a")
        g.add_edge("a", "b")
        g.add_edge("b", END)
        compiled = g.compile(checkpointer=cp)

        events = list(compiled.stream({"seed": 1}, config=config, stream_mode="updates"))
        assert any("a" in e for e in events)
        assert not any("b" in e for e in events)


def test_p2_dynamic_interrupt_and_resume():
    with tempfile.TemporaryDirectory() as tmp:
        cp = json_file_checkpointer(str(Path(tmp) / "cp"))
        config = {"configurable": {"thread_id": "dyn-interrupt-1"}}

        def ask(ctx: NodeContext) -> NodeUpdate:
            answer = ctx.interrupt({"question": "approve?"})
            return ctx.publish(
                artifact={"answer": answer, "done": True},
                category_slug="general",
            )

        g = Graph()
        g.add_node("ask", ask)
        g.add_edge(START, "ask")
        g.add_edge("ask", END)
        compiled = g.compile(checkpointer=cp)

        halted = compiled.invoke({}, config=config)
        assert halted.get("__interrupt__") is True
        assert halted.get("__interrupt_payload__") == {"question": "approve?"}
        assert compiled.last_tracker is not None
        interrupt_events = list(compiled.last_tracker.events)

        finished = compiled.invoke({"__resume__": "yes"}, config=config)
        assert finished.get("answer") == "yes"
        assert finished.get("done") is True
        assert any(e.get("type") == "interrupt" for e in interrupt_events)
