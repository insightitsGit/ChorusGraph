"""Pluggable agent pattern strategies (DESIGN §7.8)."""

from __future__ import annotations

from chorusgraph.agents.strategies.base import AgentContext, AgentRunResult, AgentStrategy
from chorusgraph.agents.strategies.plan_solve_strategy import PlanSolveStrategy
from chorusgraph.agents.strategies.react_strategy import ReactStrategy
from chorusgraph.agents.strategies.reflection_strategy import ReflectionStrategy

STRATEGY_REGISTRY: dict[str, AgentStrategy] = {
    "react": ReactStrategy(),
    "reflection": ReflectionStrategy(),
    "plan_solve": PlanSolveStrategy(),
}


def get_strategy(pattern: str) -> AgentStrategy:
    if pattern not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown agent pattern: {pattern}. Choose from {list(STRATEGY_REGISTRY)}")
    return STRATEGY_REGISTRY[pattern]
