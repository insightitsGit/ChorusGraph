"""Compound deterministic path + canonical rubric (no Gemini)."""

from __future__ import annotations

from unittest.mock import MagicMock

from benchmark.measure import score_task_success
from benchmark.rubric import score_by_canonical
from chorusgraph.examples.finance_agent.nodes import (
    make_compound_tool_handler,
    make_researcher_handler,
    make_writer_handler,
)
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime
from chorusgraph.nodes.tool import compound_interest
from chorusgraph.transforms.intent import needs_compound_tool, parse_compound_params
from chorusgraph.transforms.templates import template_compound_response, try_template_draft


_COMPOUND_MSG = (
    "If I invest $10,000 at 5% annual interest compounded monthly for 3 years, "
    "what is the future value?"
)


def test_parse_compound_params_benchmark_prompt():
    params = parse_compound_params(_COMPOUND_MSG)
    assert params is not None
    assert params["principal"] == 10000.0
    assert params["annual_rate_pct"] == 5.0
    assert params["years"] == 3.0
    assert params["compounds_per_year"] == 12


def test_needs_compound_tool_fx_message_false():
    assert not needs_compound_tool("What is the USD to EUR exchange rate today?")


def test_template_compound_response_matches_tool():
    data = compound_interest(10000, 5, 3, 12)
    text = template_compound_response(data)
    assert text is not None
    assert "11,614.72" in text


def test_researcher_routes_compound_before_fx():
    runtime = FinanceRuntime(tenant_id="compound-route-test")
    researcher = make_researcher_handler(runtime)
    out = researcher({"message": _COMPOUND_MSG, "conversation_history": []})
    assert out["needs_tool"] is True
    assert out["tool_name"] == "compound_interest"
    assert out["tool_args"]["principal"] == 10000.0


def test_compound_tool_handler_no_llm():
    runtime = FinanceRuntime(tenant_id="compound-tool-test")
    handler = make_compound_tool_handler(runtime)
    out = handler({"message": _COMPOUND_MSG, "tool_calls": []})
    assert out["tool_result"]["future_value"] == 11614.72
    assert out["rule_chain"][0].startswith("compound_tool ok=True")


def test_writer_compound_template_without_gemini():
    runtime = FinanceRuntime(tenant_id="compound-writer-test", cortex=None)
    runtime.gemini = MagicMock()
    data = compound_interest(10000, 5, 3, 12)
    writer = make_writer_handler(runtime)
    out = writer(
        {
            "message": _COMPOUND_MSG,
            "conversation_history": [],
            "tool_result": data,
            "tool_results": [],
        }
    )
    assert "11,614.72" in out["draft_response"]
    assert out["rule_chain"][0] == "writer=template_draft"
    runtime.gemini.generate.assert_not_called()


def test_rubric_compound_requires_correct_fv():
    data = compound_interest(10000, 5, 3, 12)
    answer = template_compound_response(data)
    assert score_by_canonical(
        canonical_id="compound_savings",
        message=_COMPOUND_MSG,
        answer=answer or "",
        tool_result=data,
    )
    assert not score_by_canonical(
        canonical_id="compound_savings",
        message=_COMPOUND_MSG,
        answer="I cannot help with compound interest.",
        tool_result=data,
    )


def test_rubric_fx_rejects_wrong_pair():
    assert score_by_canonical(
        canonical_id="usd_eur",
        message="USD to EUR?",
        answer="The exchange rate is 1 USD = 0.9123 EUR today.",
        tool_result={"rate": 0.9123, "from_currency": "USD", "to_currency": "EUR"},
    )
    assert not score_by_canonical(
        canonical_id="usd_jpy",
        message="USD to JPY?",
        answer="The exchange rate is 1 USD = 0.9123 EUR today.",
        tool_result={"rate": 0.9123, "from_currency": "USD", "to_currency": "EUR"},
    )


def test_rubric_fx_false_pass_with_unrelated_decimal_fails():
    """Old rubric false-pass: FX decimal in compound refusal should not pass usd_jpy."""
    assert not score_task_success(
        message="What is the USD to JPY exchange rate today?",
        answer="I only have EUR data. The USD/EUR rate is 0.8785.",
        canonical_id="usd_jpy",
    )


def test_try_template_draft_compound():
    data = compound_interest(10000, 5, 3, 12)
    draft = try_template_draft(message=_COMPOUND_MSG, tool_result=data)
    assert draft is not None
    assert "11,614.72" in draft
