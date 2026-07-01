"""Tests for finance tool node (real API, no mocks)."""

from __future__ import annotations

import pytest

from chorusgraph.nodes.tool import (
    compound_interest,
    default_finance_registry,
    fetch_exchange_rate,
    run_tool,
)


def test_fetch_exchange_rate_real():
    result = fetch_exchange_rate("USD", "EUR")
    assert result["from_currency"] == "USD"
    assert result["to_currency"] == "EUR"
    assert result["rate"] > 0
    assert result["source"] == "frankfurter.app (ECB)"
    assert result["date"]


def test_compound_interest_deterministic():
    result = compound_interest(1000, 5.0, 10, compounds_per_year=12)
    assert result["future_value"] > 1000
    assert result["interest_earned"] == pytest.approx(result["future_value"] - 1000, rel=1e-6)


def test_registry_run_with_retry_metadata():
    registry = default_finance_registry()
    out = registry.run("fetch_exchange_rate", from_currency="EUR", to_currency="GBP")
    assert out.ok
    assert out.data["rate"] > 0
    assert out.attempts >= 1
    assert out.duration_ms >= 0
