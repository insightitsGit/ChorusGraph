"""ONNX-first internal transforms — no LLM on deterministic paths."""

from __future__ import annotations

from unittest.mock import MagicMock

from chorusgraph.examples.finance_agent.nodes import make_writer_handler
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime
from chorusgraph.policy.embedder_guard import build_guarded_cache
from chorusgraph.transforms.projector import project_text
from chorusgraph.transforms.templates import template_fx_response, template_multi_fx_response, try_template_draft


def test_project_text_returns_64d_vector():
    cache = build_guarded_cache("transform-test")
    raw, envelope = project_text(cache, "USD to EUR exchange rate")
    assert raw.shape == (384,)
    assert len(envelope.vector) == 64


def test_template_fx_response_includes_rate():
    text = template_fx_response(
        {"from_currency": "USD", "to_currency": "EUR", "rate": 0.9123, "date": "2026-01-01"}
    )
    assert text is not None
    assert "0.9123" in text
    assert "USD" in text
    assert "EUR" in text


def test_template_multi_fx_response():
    text = template_multi_fx_response(
        [
            {"from_currency": "USD", "to_currency": "EUR", "rate": 0.91},
            {"from_currency": "USD", "to_currency": "GBP", "rate": 0.79},
        ]
    )
    assert text is not None
    assert "0.91" in text
    assert "0.79" in text


def test_writer_uses_template_without_gemini():
    runtime = FinanceRuntime(tenant_id="writer-template-test", cortex=None)
    runtime.gemini = MagicMock()
    writer = make_writer_handler(runtime)
    out = writer(
        {
            "message": "What is USD to EUR?",
            "conversation_history": [],
            "tool_result": {
                "from_currency": "USD",
                "to_currency": "EUR",
                "rate": 0.8765,
                "date": "2026-01-01",
            },
            "tool_results": [],
        }
    )
    assert out["draft_response"]
    assert "0.8765" in out["draft_response"]
    assert out["rule_chain"][0] == "writer=template_draft"
    runtime.gemini.generate.assert_not_called()


def test_pattern_writer_no_duplicate_call():
    from chorusgraph.examples.finance_agent.pattern_nodes import make_pattern_writer_handler

    runtime = FinanceRuntime(tenant_id="pattern-writer-test", cortex=None)
    runtime.gemini = MagicMock()
    writer = make_pattern_writer_handler(runtime)
    out = writer(
        {
            "message": "Compare USD/EUR and USD/GBP",
            "conversation_history": [],
            "tool_results": [
                {"from_currency": "USD", "to_currency": "EUR", "rate": 0.91},
                {"from_currency": "USD", "to_currency": "GBP", "rate": 0.79},
            ],
        }
    )
    assert "0.91" in out["draft_response"]
    assert "0.79" in out["draft_response"]
    assert out["rule_chain"][0] == "writer=template_draft"
    runtime.gemini.generate.assert_not_called()


def test_try_template_draft_returns_none_for_advice_only():
    assert try_template_draft(message="What bond allocation do you recommend?") is None
