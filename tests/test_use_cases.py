"""Tests for LLM-free use-case demos (patterns, cache, warm chunks, Cortex lifecycle)."""

from __future__ import annotations

from chorusgraph.examples.use_cases.cases import USE_CASES, by_pattern
from chorusgraph.examples.use_cases.run import (
    run_cache_use_case,
    run_cortex_use_case,
    run_multi_agent_use_case,
    run_plan_solve_use_case,
    run_react_use_case,
    run_reflection_use_case,
    run_warm_chunks_use_case,
)


def test_use_case_catalog_has_seven_entries():
    patterns = {uc.pattern for uc in USE_CASES}
    assert patterns == {
        "react",
        "plan_solve",
        "reflection",
        "multi_agent",
        "cache",
        "warm_chunks",
        "cortex",
    }
    assert by_pattern("warm_chunks").topology.startswith("index")
    assert by_pattern("cortex").topology.startswith("ingress")


def test_react_use_case_two_tools():
    out = run_react_use_case()
    result = out["result"]
    assert result.finished
    assert len(result.tool_calls) == 2
    assert all(tc.get("ok") for tc in result.tool_calls)


def test_plan_solve_use_case_executes_and_computes_cross():
    out = run_plan_solve_use_case()
    result = out["result"]
    assert result.finished
    assert len(result.tool_calls) == 2
    assert any(isinstance(o, dict) and o.get("computed") for o in result.observations)


def test_reflection_use_case_approves_revised_draft():
    out = run_reflection_use_case()
    result = out["result"]
    assert result.approved is True
    assert result.draft and "0.92" in result.draft
    assert "0.9900" not in (result.draft or "")


def test_multi_agent_use_case_role_pipeline():
    out = run_multi_agent_use_case()
    assert out["ledger_nodes"] == ["researcher", "writer", "validator"]
    assert out["result"].get("response")
    assert (out["result"].get("validation") or {}).get("ok") is True


def test_cache_use_case_miss_then_hit():
    out = run_cache_use_case()
    assert out["miss"].is_hit is False
    assert out["hit"].is_hit is True
    assert out["hit"].value["rate"] == 0.92
    assert out["backend"] == "prism"
    assert out["paraphrase"].is_hit is True


def test_warm_chunks_use_case_partitions():
    out = run_warm_chunks_use_case()
    assert out["ready"] is True
    assert out["kb_hits"][0]["id"] == "md1"
    assert out["catalog_hits"][0]["id"] == "cat1"
    assert out["versions"]["kb_markdown"] == "docs-v1"
    assert out["versions"]["catalog"] == "cat-v2"
    assert out["kb_after_catalog_bump"][0]["id"] == "md1"
    assert any("partition=kb_markdown" in r for r in (out["update"].get("rule_chain") or []))


def test_cortex_use_case_right_lifecycle():
    out = run_cortex_use_case()
    assert out["backend"] == "teaching_cortex"
    assert out["recall_state"]["memory_confidence"] >= 0.9
    assert "moderate risk" in (out["recall_state"]["memory_recall"] or "").lower()
    assert out["empty_recall"] is None
    assert out["digests"]
