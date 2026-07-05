"""FC/HC scenarios must use native ChorusGraph engine — no LangGraph imports.

Policy: docs/TERMINOLOGY.md — "ChorusGraph" = full native product (core.Graph + Prism stack).
LangGraph is only for FL*/HL* baselines.
"""

from __future__ import annotations

from benchmark.framework_guard import fc_hc_langgraph_offenders, fl_hl_missing_langgraph


def test_fc_hc_paths_have_no_langgraph_imports():
    offenders = fc_hc_langgraph_offenders()
    assert not offenders, "LangGraph must not appear in FC/HC code paths:\n  " + "\n  ".join(
        offenders
    )


def test_fl_hl_paths_use_langgraph():
    missing = fl_hl_missing_langgraph()
    assert not missing, "FL/HL baseline scenarios must import LangGraph:\n  " + "\n  ".join(missing)
