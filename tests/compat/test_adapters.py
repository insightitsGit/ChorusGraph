"""Compat adapter unit tests."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from chorusgraph.compat.checkpoint_import import import_checkpoints
from chorusgraph.compat.otel_exporter import ledger_to_spans
from chorusgraph.compat.tool_node import ToolNode
from chorusgraph.ledger.models import LedgerStep, RouteLedger


class _StubTool:
    name = "search"

    def invoke(self, args):
        return {"hits": [args.get("q", "")]}


def test_tool_node_duck_typing():
    node = ToolNode([_StubTool()])
    out = node.invoke({"tool_calls": [{"name": "search", "args": {"q": "test"}}]})
    assert out["tool_result"]["hits"] == ["test"]


def test_ledger_otel_exporter():
    ledger = RouteLedger(tenant_id="t", graph_id="g")
    ledger.add_step(LedgerStep(node="a", rule_chain=["r1"], cache_hit=True, parent_run_id="p1"))
    spans = ledger_to_spans(ledger)
    assert spans[0]["attributes"]["chorusgraph.cache_hit"] is True
    assert spans[0]["attributes"]["chorusgraph.parent_run_id"] == "p1"


def test_checkpoint_import_sqlite(tmp_path: Path):
    db = tmp_path / "lg.sqlite"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE checkpoints (thread_id TEXT, checkpoint TEXT, metadata TEXT)")
    conn.execute(
        "INSERT INTO checkpoints VALUES (?, ?, ?)",
        ("t1", json.dumps({"channel_values": {"x": 1}}), json.dumps({"step": 1})),
    )
    conn.commit()
    conn.close()
    dest = tmp_path / "dest"
    n = import_checkpoints(source_sqlite=db, dest_root=dest)
    assert n == 1


def test_mcp_prism_api_probe():
    try:
        from prism.api.mcp import PrismAPIMCPServer  # type: ignore
    except Exception as exc:
        pytest.skip(f"PrismAPIMCPServer not usable: {exc}")
    assert PrismAPIMCPServer is not None
