"""Scenario registry — FL/FC/HL naming (LangGraph vs ChorusGraph)."""

from __future__ import annotations

from typing import Callable, Dict, Literal, Union

from benchmark.fc1.runner import FC1Runner
from benchmark.fc2.runner import FC2Runner
from benchmark.fl1.runner import FL1Runner
from benchmark.fl2.runner import FL2Runner
from benchmark.hc1.runner import HC1Runner
from benchmark.hc2.runner import HC2Runner
from benchmark.hl1.runner import HL1Runner
from benchmark.hl2.runner import HL2Runner

ScenarioId = Literal["FL1", "FC1", "HL1", "HC1", "FL2", "FC2", "HL2", "HC2"]

# Domain x mode matrix
SCENARIO_MATRIX = {
    ("finance", "single"): ("FL1", "FC1"),
    ("finance", "multi"): ("FL2", "FC2"),
    ("healthcare", "single"): ("HL1", "HC1"),
    ("healthcare", "multi"): ("HL2", "HC2"),
}


def make_runner(scenario: ScenarioId):
    """Factory for scenario runners."""
    factories: Dict[ScenarioId, Callable[[], object]] = {
        "FL1": FL1Runner,
        "FC1": FC1Runner,
        "HL1": HL1Runner,
        "HC1": HC1Runner,
        "FL2": FL2Runner,
        "FC2": FC2Runner,
        "HL2": HL2Runner,
        "HC2": HC2Runner,
    }
    return factories[scenario]()


def langgraph_scenarios() -> tuple[ScenarioId, ...]:
    return ("FL1", "HL1", "FL2", "HL2")


def chorusgraph_scenarios() -> tuple[ScenarioId, ...]:
    return ("FC1", "HC1", "FC2", "HC2")


__all__ = [
    "SCENARIO_MATRIX",
    "ScenarioId",
    "chorusgraph_scenarios",
    "langgraph_scenarios",
    "make_runner",
]
