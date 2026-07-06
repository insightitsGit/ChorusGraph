"""Plan-Solve Agent shim."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from chorusgraph.agents.plan_utils import PlanStep, plan_tasks, _try_compute_cross
from chorusgraph.agents.policy import PlanPolicy, PlanSolveOpts
from chorusgraph.nodes.tool import ToolRegistry

__all__ = ["PlanStep", "PlanSolveResult", "plan_tasks", "run_plan_solve", "_try_compute_cross"]


@dataclass
class PlanSolveResult:
    plan: List[PlanStep] = field(default_factory=list)
    trace: List[Any] = field(default_factory=list)
    observations: List[Any] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    failed_step: Optional[int] = None


def run_plan_solve(
    *,
    question: str,
    registry: ToolRegistry,
    llm_json: Callable[[str, str], str],
    policy: Optional[PlanPolicy] = None,
    pattern_opts: Optional[PlanSolveOpts] = None,
) -> PlanSolveResult:
    from chorusgraph.agents.agent import Agent

    policy = policy or PlanPolicy(max_steps=10)
    opts = pattern_opts or PlanSolveOpts(max_plan_steps=policy.max_steps, on_step_failure="abort")
    agent = Agent(
        pattern="plan_solve",
        tools=registry,
        model=llm_json,
        policy=policy,
        pattern_opts=opts,
    )
    result = agent.run(question)
    return PlanSolveResult(
        plan=result.plan,
        trace=result.trace,
        observations=result.observations,
        tool_calls=result.tool_calls,
        failed_step=result.failed_step,
    )
