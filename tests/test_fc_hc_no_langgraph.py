"""FC/HC scenarios must use native ChorusGraph engine — no LangGraph imports.

Policy: docs/TERMINOLOGY.md — "ChorusGraph" = full native product (core.Graph + Prism stack).
LangGraph is only for FL*/HL* baselines.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]

_FC_HC_ROOTS = (
    _REPO / "benchmark" / "fc1",
    _REPO / "benchmark" / "fc2",
    _REPO / "benchmark" / "hc1",
    _REPO / "benchmark" / "hc2",
)

# FC1 graph builder lives here (not under benchmark/fc1/).
_FC1_GRAPH = _REPO / "chorusgraph" / "examples" / "finance_agent" / "patterns_graph.py"


def _langgraph_imports_in_file(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "langgraph" or alias.name.startswith("langgraph."):
                    hits.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == "langgraph" or node.module.startswith("langgraph.")):
                hits.append(f"from {node.module} import ...")
    return hits


def test_fc_hc_paths_have_no_langgraph_imports():
    offenders: list[str] = []
    for root in _FC_HC_ROOTS:
        for path in sorted(root.rglob("*.py")):
            for hit in _langgraph_imports_in_file(path):
                offenders.append(f"{path.relative_to(_REPO)}: {hit}")
    for hit in _langgraph_imports_in_file(_FC1_GRAPH):
        offenders.append(f"{_FC1_GRAPH.relative_to(_REPO)}: {hit}")
    assert not offenders, "LangGraph must not appear in FC/HC code paths:\n  " + "\n  ".join(offenders)
