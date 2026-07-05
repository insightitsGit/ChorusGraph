"""Ensure core pyproject dependencies match hard imports on ``import chorusgraph``."""

from __future__ import annotations

from pathlib import Path


def _core_dependency_lines() -> list[str]:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    in_deps = False
    lines: list[str] = []
    for line in text.splitlines():
        if line.strip() == "dependencies = [":
            in_deps = True
            continue
        if in_deps:
            if line.strip().startswith("]"):
                break
            lines.append(line.strip().strip(",").strip('"'))
    return lines


def test_core_dependencies_include_prism_stack():
    deps = _core_dependency_lines()
    joined = "\n".join(deps)
    assert "prismlib-plus>=" in joined, (
        "PrismCache (prism.cache) requires prismlib-plus in core deps"
    )
    assert "prismresonance>=" in joined, "ResonanceBus requires prismresonance in core deps"


def test_import_chorusgraph_smoke():
    import chorusgraph
    from chorusgraph import END, START, ChorusStack, Graph

    assert chorusgraph.__version__
    assert Graph is not None
    assert ChorusStack is not None
    assert START is not None
    assert END is not None
