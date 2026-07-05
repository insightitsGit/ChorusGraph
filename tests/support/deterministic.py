"""Deterministic test tier — replay recorded HTTP + stub Gemini (E1)."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from tests.support.stub_gemini import DeterministicGeminiStub

CASSETTE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "cassettes"

_PATCHERS: list[Any] = []
_REAL_INSTRUMENTED_GEMINI: type | None = None


def real_instrumented_gemini_client() -> type:
    """Original InstrumentedGeminiClient (for unit tests that mock the API layer)."""
    assert _REAL_INSTRUMENTED_GEMINI is not None
    return _REAL_INSTRUMENTED_GEMINI


def is_live_mode(config: pytest.Config | None = None) -> bool:
    if os.environ.get("CHORUSGRAPH_LIVE") == "1":
        return True
    if config is not None:
        markexpr = getattr(config.option, "markexpr", "") or ""
        if "live" in markexpr and "not live" not in markexpr:
            return True
    return False


def is_deterministic_mode(config: pytest.Config | None = None) -> bool:
    return not is_live_mode(config)


def _cassette_key(url: str, params: dict[str, Any]) -> str:
    base = str(params.get("from", "")).upper()
    quote = str(params.get("to", "")).upper()
    return f"latest_{base.lower()}_{quote.lower()}"


def _load_frankfurter_cassette(key: str) -> dict[str, Any]:
    path = CASSETTE_ROOT / "frankfurter" / f"{key}.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing Frankfurter cassette: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class _CassetteResponse:
    def __init__(self, *, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("cassette error", request=None, response=self)  # type: ignore[arg-type]

    def json(self) -> dict[str, Any]:
        return self._payload


class _CassetteHttpxClient:
    """Replay Frankfurter cassettes for tool tests — no outbound network."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> _CassetteHttpxClient:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def get(
        self, url: str, *, params: dict[str, Any] | None = None, **kwargs: Any
    ) -> _CassetteResponse:
        params = dict(params or {})
        if "frankfurter.app" not in url:
            raise RuntimeError(f"Deterministic tier: unexpected HTTP GET {url!r} (no cassette)")
        key = _cassette_key(url, params)
        cassette = _load_frankfurter_cassette(key)
        resp = cassette["response"]
        return _CassetteResponse(status_code=int(resp["status_code"]), payload=dict(resp["json"]))


def _deterministic_resolve_gemini_api_key() -> None:
    return None


def start_deterministic_patches() -> None:
    """Install cassettes + Gemini stubs (call from pytest_configure before collection)."""
    global _PATCHERS, _REAL_INSTRUMENTED_GEMINI
    if _PATCHERS:
        return
    import benchmark.shared.instrumented_gemini as ig

    _REAL_INSTRUMENTED_GEMINI = ig.InstrumentedGeminiClient
    os.environ["CHORUSGRAPH_DETERMINISTIC"] = "1"
    os.environ.pop("GEMINI_API_KEY", None)
    os.environ.pop("GOOGLE_API_KEY", None)
    targets = [
        "httpx.Client",
        "chorusgraph.examples.finance_agent.gemini_client.resolve_gemini_api_key",
        "chorusgraph.examples.finance_agent.gemini_client.GeminiClient",
        "benchmark.shared.instrumented_gemini.InstrumentedGeminiClient",
    ]
    values = [
        _CassetteHttpxClient,
        _deterministic_resolve_gemini_api_key,
        DeterministicGeminiStub,
        DeterministicGeminiStub,
    ]
    for target, value in zip(targets, values, strict=True):
        p = patch(target, value)
        p.start()
        _PATCHERS.append(p)


def stop_deterministic_patches() -> None:
    global _PATCHERS
    while _PATCHERS:
        _PATCHERS.pop().stop()
    os.environ.pop("CHORUSGRAPH_DETERMINISTIC", None)
