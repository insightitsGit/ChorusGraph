"""Pytest configuration — E1 deterministic tier (default) vs live integration."""

from __future__ import annotations

import pytest

from tests.support.deterministic import (
    is_deterministic_mode,
    start_deterministic_patches,
    stop_deterministic_patches,
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "live: live Gemini/API integration (requires keys + network)"
    )
    config.addinivalue_line("markers", "network: tests that require outbound network")
    if is_deterministic_mode(config):
        start_deterministic_patches()


def pytest_unconfigure(config: pytest.Config) -> None:
    if is_deterministic_mode(config):
        stop_deterministic_patches()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if is_deterministic_mode(config):
        skip_live = pytest.mark.skip(reason="live integration — run with: pytest -m live")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)
