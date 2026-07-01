"""Integration tests for the demo graph + adapter."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from chorusgraph import SqliteLedgerSink, get_run, list_runs, wrap
from chorusgraph.examples.demo_graph import GRAPH_ID, TENANT_ID, build_demo_graph


def test_demo_graph_short_path_records_nodes_and_branch():
    sink = SqliteLedgerSink(":memory:")
    wrapped = wrap(
        build_demo_graph(),
        tenant_id=TENANT_ID,
        graph_id=GRAPH_ID,
        sink=sink,
    )
    result = wrapped.invoke(
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
    assert result["response"] == "short:hi"
    ledger = wrapped.last_ledger
    assert ledger is not None
    nodes = [s.node for s in ledger.steps]
    assert nodes == ["analyze", "route_decision", "short_path"]

    route_step = ledger.steps[1]
    assert route_step.edge_taken == "short_path"
    assert route_step.rule_chain == ["score_lte_5", "route=short_path"]

    analyze_step = ledger.steps[0]
    assert analyze_step.rule_chain is not None
    assert len(analyze_step.rule_chain) > 0

    persisted = get_run(sink, ledger.run_id)
    assert persisted is not None
    assert [s.node for s in persisted.steps] == nodes


def test_demo_graph_long_path_branch():
    sink = SqliteLedgerSink(":memory:")
    wrapped = wrap(build_demo_graph(), tenant_id=TENANT_ID, graph_id=GRAPH_ID, sink=sink)
    result = wrapped.invoke(
        {
            "tenant_id": TENANT_ID,
            "message": "hello world!",
            "score": 0,
            "route": "",
            "rule_chain": [],
            "prism_sequence": [],
            "response": "",
        }
    )
    assert result["response"] == "long:hello world!"
    ledger = wrapped.last_ledger
    assert ledger is not None
    assert [s.node for s in ledger.steps] == ["analyze", "route_decision", "long_path"]
    assert ledger.steps[1].edge_taken == "long_path"
    assert ledger.steps[1].rule_chain == ["score_gt_5", "route=long_path"]


def test_list_runs_by_graph_and_tenant():
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
    runs = list_runs(sink, graph_id=GRAPH_ID, tenant_id=TENANT_ID)
    assert len(runs) == 1


@pytest.mark.skipif(
    not Path(r"c:\code\InsightitsAIAgent\meeting-scheduler\website_hub\graph.py").exists(),
    reason="website_hub not available locally",
)
def test_website_hub_greeting_stretch_demo():
    meeting_scheduler = Path(r"c:\code\InsightitsAIAgent\meeting-scheduler")
    if str(meeting_scheduler) not in sys.path:
        sys.path.insert(0, str(meeting_scheduler))

    from website_hub.graph import get_graph

    sink = SqliteLedgerSink(":memory:")
    wrapped = wrap(
        get_graph(),
        tenant_id="insightits_website",
        graph_id="website_hub",
        sink=sink,
    )
    result = wrapped.invoke(
        {
            "message": "hello",
            "conversation_history": [],
            "prism_sequence": [],
            "tenant_id": "insightits_website",
            "pipeline_trace": [],
        }
    )
    assert result.get("route") == "greeting"
    assert result.get("response")
    ledger = wrapped.last_ledger
    assert ledger is not None
    nodes = [s.node for s in ledger.steps]
    assert nodes == ["resolve_session", "classify_intent", "respond_quick"]
    assert ledger.steps[1].edge_taken == "respond_quick"
