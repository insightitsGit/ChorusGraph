"""Ensure LangGraph is not a core library dependency."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


def test_pyproject_core_dependencies_exclude_langgraph():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    in_deps = False
    for line in text.splitlines():
        if line.strip() == "dependencies = [":
            in_deps = True
            continue
        if in_deps:
            if line.strip().startswith("]"):
                break
            assert "langgraph" not in line.lower(), f"LangGraph must not be a core dep: {line.strip()}"


def test_chorusgraph_package_has_no_langgraph_imports():
    root = Path("chorusgraph")
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "langgraph" or alias.name.startswith("langgraph."):
                        offenders.append(f"{path}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "langgraph" or mod.startswith("langgraph."):
                    offenders.append(f"{path}: from {mod}")
    assert not offenders, "chorusgraph/ must not import langgraph:\n  " + "\n  ".join(offenders)


@pytest.mark.parametrize(
    "extra",
    ["langgraph", "benchmark"],
)
def test_langgraph_optional_extra_declared(extra: str):
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert f"{extra} = [" in text
    assert "langgraph>=" in text
