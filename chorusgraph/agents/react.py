"""ReAct Agent shim."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from chorusgraph.agents.policy import PlanPolicy, ReActOpts
from chorusgraph.nodes.tool import ToolRegistry


@dataclass
class ReActResult:
    trace: List[Any] = field(default_factory=list)
    observations: List[Any] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    finished: bool = False
    finish_reason: Optional[str] = None


def run_react(
    *,
    question: str,
    registry: ToolRegistry,
    llm_json: Callable[[str, str], str],
    policy: Optional[PlanPolicy] = None,
    scratchpad_prefix: str = "",
    pattern_opts: Optional[ReActOpts] = None,
) -> ReActResult:
    from chorusgraph.agents.agent import Agent

    policy = policy or PlanPolicy(max_steps=6)
    opts = pattern_opts or ReActOpts(max_tool_calls=policy.max_steps)
    agent = Agent(
        pattern="react",
        tools=registry,
        model=llm_json,
        policy=policy,
        pattern_opts=opts,
    )
    result = agent.run(question, scratchpad_prefix=scratchpad_prefix)
    return ReActResult(
        trace=result.trace,
        observations=result.observations,
        tool_calls=result.tool_calls,
        finished=result.finished,
        finish_reason=result.finish_reason,
    )
