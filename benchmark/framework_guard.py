"""Framework split guard — FC/HC native only, FL/HL LangGraph only."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, List

_REPO = Path(__file__).resolve().parents[1]

_FC_HC_ROOTS = (
    _REPO / "benchmark" / "fc1",
    _REPO / "benchmark" / "fc2",
    _REPO / "benchmark" / "hc1",
    _REPO / "benchmark" / "hc2",
)

_FL_HL_ROOTS = (
    _REPO / "benchmark" / "fl1",
    _REPO / "benchmark" / "fl2",
    _REPO / "benchmark" / "hl1",
    _REPO / "benchmark" / "hl2",
)

_FC1_GRAPH = _REPO / "chorusgraph" / "examples" / "finance_agent" / "patterns_graph.py"

_CHORUS_NATIVE_MARKERS = (
    "chorusgraph.core",
    "from chorusgraph.core import",
    "chorusgraph.core.Graph",
    "build_react_graph",
    "build_finance_graph_fc2",
    "build_healthcare_graph_hc1",
    "build_healthcare_graph_hc2",
)


def _langgraph_imports_in_file(path: Path) -> List[str]:
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


def _iter_py_files(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if root.is_file():
            yield root
            continue
        for path in sorted(root.rglob("*.py")):
            yield path


def fc_hc_langgraph_offenders() -> List[str]:
    offenders: list[str] = []
    for path in _iter_py_files(_FC_HC_ROOTS):
        for hit in _langgraph_imports_in_file(path):
            offenders.append(f"{path.relative_to(_REPO)}: {hit}")
    for hit in _langgraph_imports_in_file(_FC1_GRAPH):
        offenders.append(f"{_FC1_GRAPH.relative_to(_REPO)}: {hit}")
    return offenders


def fl_hl_missing_langgraph() -> List[str]:
    """Each FL/HL scenario must wire LangGraph in runner.py or graph.py."""
    missing: list[str] = []
    for root in _FL_HL_ROOTS:
        if not root.is_dir():
            continue
        candidates = list(root.glob("runner.py")) + list(root.glob("graph.py"))
        if not candidates:
            missing.append(str(root.relative_to(_REPO)))
            continue
        if not any("langgraph" in p.read_text(encoding="utf-8") for p in candidates):
            missing.append(str(root.relative_to(_REPO)))
    return missing


def verify_framework_split() -> List[str]:
    """
    Confirm benchmark matrix wiring: C=ChorusGraph native, L=LangGraph baseline.

    Raises ``BenchmarkWiringError`` on violation.
    """
    from benchmark.wiring import BenchmarkWiringError

    ok: list[str] = []

    offenders = fc_hc_langgraph_offenders()
    if offenders:
        raise BenchmarkWiringError(
            "FC/HC must not import LangGraph:\n  " + "\n  ".join(offenders)
        )
    ok.append("FC/HC: no LangGraph imports (native engine only)")

    missing_lg = fl_hl_missing_langgraph()
    if missing_lg:
        raise BenchmarkWiringError(
            "FL/HL baseline scenarios must use LangGraph:\n  " + "\n  ".join(missing_lg)
        )
    ok.append("FL/HL: LangGraph baseline present")

    for scenario, root in (
        ("FC1", _REPO / "benchmark" / "fc1"),
        ("FC2", _REPO / "benchmark" / "fc2"),
        ("HC1", _REPO / "benchmark" / "hc1"),
        ("HC2", _REPO / "benchmark" / "hc2"),
    ):
        text = " ".join(p.read_text(encoding="utf-8") for p in root.rglob("*.py"))
        if not any(m in text for m in _CHORUS_NATIVE_MARKERS):
            raise BenchmarkWiringError(f"{scenario} runner missing native ChorusGraph wiring")
    ok.append("FC/HC: native graph builders referenced")

    return ok


__all__ = [
    "fc_hc_langgraph_offenders",
    "fl_hl_missing_langgraph",
    "verify_framework_split",
]
