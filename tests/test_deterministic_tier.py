"""E1 — deterministic tier smoke tests."""

from __future__ import annotations

import pytest

from chorusgraph.examples.finance_agent import gemini_client as gc
from chorusgraph.nodes.tool import fetch_exchange_rate


def test_frankfurter_replays_from_cassette_without_network():
    out = fetch_exchange_rate("USD", "EUR")
    assert out["from_currency"] == "USD"
    assert out["to_currency"] == "EUR"
    assert out["rate"] == pytest.approx(0.87352)
    assert out["date"] == "2026-07-03"


def test_gemini_key_not_resolved_in_default_tier():
    assert gc.resolve_gemini_api_key() is None
