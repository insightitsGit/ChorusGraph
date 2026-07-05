"""T2 — Command routing and interrupt-returns-value."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from chorusgraph.core import END, START, Graph
from chorusgraph.core.channels import NodeUpdate
from chorusgraph.core.node import Command, NodeContext
from chorusgraph.core.persistence import json_file_checkpointer


def test_command_routes_and_updates():
    visits: list[str] = []

    def router(ctx: NodeContext) -> Command:
        pick = ctx.read().get("pick", "left")
        visits.append("router")
        target = "right" if pick == "long_path" else "left"
        return Command(
            update={"branch": pick, "raw_output": pick},
            goto=target,
        )

    def left(ctx: NodeContext) -> NodeUpdate:
        visits.append("left")
        return ctx.publish(artifact={"out": "L"}, category_slug="left")

    def right(ctx: NodeContext) -> NodeUpdate:
        visits.append("right")
        return ctx.publish(artifact={"out": "R"}, category_slug="right")

    g = Graph()
    g.add_node("router", router)
    g.add_node("left", left, category_slug="left")
    g.add_node("right", right, category_slug="long_path")
    g.add_edge(START, "router")
    g.add_conditional_edges(
        "router", lambda v: v.get("branch", "left"), {"left": "left", "long_path": "right"}
    )
    g.add_edge("left", END)
    g.add_edge("right", END)

    out = g.compile().invoke({"pick": "long_path"})
    assert visits == ["router", "right"]
    assert out.get("out") == "R"


def test_command_undeclared_goto_raises():
    def bad(ctx: NodeContext) -> Command:
        return Command(update={"x": 1}, goto="nowhere")

    g = Graph()
    g.add_node("bad", bad)
    g.add_edge(START, "bad")
    g.add_edge("bad", END)
    with pytest.raises(ValueError, match="declared successors"):
        g.compile().invoke({})


def test_interrupt_returns_resume_value_in_node():
    with tempfile.TemporaryDirectory() as tmp:
        cp = json_file_checkpointer(str(Path(tmp) / "cp"))
        config = {"configurable": {"thread_id": "cmd-interrupt-1"}}

        def ask(ctx: NodeContext) -> NodeUpdate:
            approved = ctx.interrupt({"question": "approve?"})
            return ctx.publish(
                artifact={"approved": approved},
                category_slug="general",
            )

        g = Graph()
        g.add_node("ask", ask)
        g.add_edge(START, "ask")
        g.add_edge("ask", END)
        compiled = g.compile(checkpointer=cp)

        halted = compiled.invoke({}, config=config)
        assert halted.get("__interrupt__") is True

        finished = compiled.invoke({"__resume__": "yes"}, config=config)
        assert finished.get("approved") == "yes"
