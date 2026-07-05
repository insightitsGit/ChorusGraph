"""Postgres checkpointer — skipped unless CHORUSGRAPH_PG_DSN is set."""

from __future__ import annotations

import os

import pytest

from chorusgraph.core import END, START, Graph
from chorusgraph.core.channels import NodeUpdate
from chorusgraph.core.node import NodeContext
from chorusgraph.core.persistence import postgres_checkpointer

PG_DSN = os.environ.get("CHORUSGRAPH_PG_DSN")


@pytest.mark.skipif(not PG_DSN, reason="CHORUSGRAPH_PG_DSN not configured")
@pytest.mark.asyncio
async def test_postgres_checkpoint_resume():
    cp = postgres_checkpointer(PG_DSN)
    config = {"configurable": {"thread_id": "pg-resume-test"}}

    def n(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"ok": True}, category_slug="general")

    g = Graph()
    g.add_node("n", n)
    g.add_edge(START, "n")
    g.add_edge("n", END)
    compiled = g.compile(checkpointer=cp)
    compiled.invoke({"x": 1}, config=config)
    snap = compiled.get_state(config)
    assert snap.values.get("x") == 1
