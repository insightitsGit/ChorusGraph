"""Reflection Agent shim."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from chorusgraph.agents.policy import PlanPolicy, ReflectionOpts


@dataclass
class ValidationVerdict:
    approved: bool
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReflectionResult:
    draft: str
    approved: bool
    trace: List[Any] = field(default_factory=list)
    passes: int = 0
    validation: Dict[str, Any] = field(default_factory=dict)


def run_reflection(
    *,
    initial_draft: str,
    validate: Callable[[str], ValidationVerdict],
    revise: Callable[[str], str],
    policy: Optional[PlanPolicy] = None,
    pattern_opts: Optional[ReflectionOpts] = None,
) -> ReflectionResult:
    from chorusgraph.agents.agent import Agent
    from chorusgraph.nodes.tool import ToolRegistry

    policy = policy or PlanPolicy(max_reflection_passes=3)
    opts = pattern_opts or ReflectionOpts(max_revisions=policy.max_reflection_passes)
    agent = Agent(
        pattern="reflection",
        tools=ToolRegistry(),
        model=lambda _s, _u: "{}",
        policy=policy,
        pattern_opts=opts,
    )
    result = agent.run("", initial_draft=initial_draft, validate=validate, revise=revise)
    return ReflectionResult(
        draft=result.draft or initial_draft,
        approved=bool(result.approved),
        trace=result.trace,
        passes=result.passes,
        validation=result.validation,
    )
