"""T1 — per-node pending writes and mid-step resume."""

from __future__ import annotations

import tempfile
from pathlib import Path

from chorusgraph.core import END, Graph, START
from chorusgraph.core.channels import NodeUpdate, publish_update
from chorusgraph.core.node import NodeContext
from chorusgraph.core.pending_writes import MidStepAbort, PendingWriteStore, node_update_from_dict, node_update_to_dict
from chorusgraph.core.persistence import json_file_checkpointer


def test_pending_write_store_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        store = PendingWriteStore(tmp)
        config = {"configurable": {"thread_id": "t-roundtrip"}}
        update = publish_update(
            hop="a",
            artifact={"v": 1},
            vector=[0.0] * 64,
            category_slug="general",
            rule_chain=["a"],
            turn_id=0,
        )
        store.put(config, 2, "a", update)
        loaded = store.list_for_step(config, 2)
        assert "a" in loaded
        assert loaded["a"].artifacts == update.artifacts
        store.clear_step(config, 2)
        assert store.list_for_step(config, 2) == {}


def test_node_update_json_serializable():
    update = publish_update(
        hop="x",
        artifact={"k": "v"},
        vector=[0.1] * 64,
        category_slug="general",
        rule_chain=["r"],
        turn_id=1,
    )
    restored = node_update_from_dict(node_update_to_dict(update))
    assert restored.rule_chain == update.rule_chain
    assert restored.envelopes[0]["agent_id"] == "x"


def test_parallel_nodes_crash_resume_only_reruns_failed():
    """Exit test: A/B complete, C crashes; resume skips A/B re-execution."""
    with tempfile.TemporaryDirectory() as tmp:
        cp = json_file_checkpointer(str(Path(tmp) / "cp"))
        config = {"configurable": {"thread_id": "pending-parallel-1"}}
        counts = {"split": 0, "a": 0, "b": 0, "c": 0}
        c_failures = {"n": 0}

        def split(ctx: NodeContext) -> NodeUpdate:
            counts["split"] += 1
            return ctx.publish(artifact={"split": True, "raw_output": "split"}, category_slug="general")

        def a(ctx: NodeContext) -> NodeUpdate:
            counts["a"] += 1
            return ctx.publish(artifact={"a": counts["a"], "raw_output": "a"}, category_slug="general")

        def b(ctx: NodeContext) -> NodeUpdate:
            counts["b"] += 1
            return ctx.publish(artifact={"b": counts["b"], "raw_output": "b"}, category_slug="general")

        def c(ctx: NodeContext) -> NodeUpdate:
            counts["c"] += 1
            if c_failures["n"] == 0:
                c_failures["n"] += 1
                raise MidStepAbort({}, super_step=ctx.super_step, active_nodes={"a", "b", "c"})
            return ctx.publish(artifact={"c": counts["c"], "raw_output": "c"}, category_slug="general")

        g = Graph()
        g.add_node("split", split)
        g.add_node("a", a)
        g.add_node("b", b)
        g.add_node("c", c)
        g.add_edge(START, "split")
        g.add_fan_out("split", "a", "b", "c")
        g.add_edge("a", END)
        g.add_edge("b", END)
        g.add_edge("c", END)
        compiled = g.compile(checkpointer=cp)

        first = compiled.invoke({"seed": 1}, config=config)
        assert first.get("__mid_step_abort__") is True
        assert counts == {"split": 1, "a": 1, "b": 1, "c": 1}

        second = compiled.invoke(None, config=config)
        assert "__mid_step_abort__" not in second
        assert counts == {"split": 1, "a": 1, "b": 1, "c": 2}
        assert second.get("a") == 1
        assert second.get("b") == 1
        assert second.get("c") == 2


def test_clean_run_matches_resume_run():
    with tempfile.TemporaryDirectory() as tmp:
        cp_clean = json_file_checkpointer(str(Path(tmp) / "cp-clean"))
        cp_resume = json_file_checkpointer(str(Path(tmp) / "cp-resume"))

        def split(ctx: NodeContext) -> NodeUpdate:
            return ctx.publish(artifact={"split": True}, category_slug="general")

        def leaf(name: str):
            def fn(ctx: NodeContext) -> NodeUpdate:
                return ctx.publish(artifact={name: 1}, category_slug="general")

            return fn

        def build(cp):
            g = Graph()
            g.add_node("split", split)
            for n in ("a", "b", "c"):
                g.add_node(n, leaf(n))
            g.add_edge(START, "split")
            g.add_fan_out("split", "a", "b", "c")
            for n in ("a", "b", "c"):
                g.add_edge(n, END)
            return g.compile(checkpointer=cp)

        clean = build(cp_clean)
        clean_out = clean.invoke({"seed": 1}, config={"configurable": {"thread_id": "clean"}})

        counts = {"c": 0}

        def c_crash(ctx: NodeContext) -> NodeUpdate:
            counts["c"] += 1
            if counts["c"] == 1:
                raise MidStepAbort({}, super_step=ctx.super_step, active_nodes=set())
            return ctx.publish(artifact={"c": 1}, category_slug="general")

        g2 = Graph()
        g2.add_node("split", split)
        g2.add_node("a", leaf("a"))
        g2.add_node("b", leaf("b"))
        g2.add_node("c", c_crash)
        g2.add_edge(START, "split")
        g2.add_fan_out("split", "a", "b", "c")
        for n in ("a", "b", "c"):
            g2.add_edge(n, END)
        resumed = g2.compile(checkpointer=cp_resume)
        cfg = {"configurable": {"thread_id": "resume"}}
        resumed.invoke({"seed": 1}, config=cfg)
        resume_out = resumed.invoke(None, config=cfg)

        for key in ("a", "b", "c", "split"):
            assert clean_out.get(key) == resume_out.get(key)
