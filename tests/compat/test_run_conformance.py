"""Conformance corpus execution."""

from __future__ import annotations

import pytest

from tests.compat.test_conformance import PATTERNS


@pytest.mark.parametrize("name,builder", PATTERNS)
def test_conformance_pattern_compiles_and_runs(name, builder):
    compiled = builder()
    cfg = {"configurable": {"thread_id": f"compat-{name}"}}
    if name == "interrupt":
        out = compiled.invoke({}, config=cfg)
        assert out.get("__interrupt__") is True
        return
    out = compiled.invoke({}, config=cfg)
    assert isinstance(out, dict)
