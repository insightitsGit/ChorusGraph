"""Strategy protocol and shared result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

from chorusgraph.agents.loop import AgentTraceStep
from chorusgraph.agents.policy import (
    BeliefPolicy,
    PatternOpts,
    PlanPolicy,
    PlanSolveOpts,
    ReActOpts,
    ReflectionOpts,
)
from chorusgraph.nodes.tool import ToolRegistry


@dataclass
class AgentRunResult:
    trace: List[AgentTraceStep] = field(default_factory=list)
    observations: List[Any] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    finished: bool = False
    finish_reason: Optional[str] = None
    draft: Optional[str] = None
    approved: Optional[bool] = None
    validation: Dict[str, Any] = field(default_factory=dict)
    plan: List[Any] = field(default_factory=list)
    failed_step: Optional[int] = None
    passes: int = 0


@dataclass
class AgentContext:
    question: str
    registry: ToolRegistry
    llm_json: Callable[[str, str], str]
    llm_text: Optional[Callable[[str, str], str]] = None
    policy: PlanPolicy = field(default_factory=PlanPolicy)
    pattern_opts: PatternOpts = field(default_factory=ReActOpts)
    belief: BeliefPolicy = field(default_factory=BeliefPolicy)
    scratchpad_prefix: str = ""
    initial_draft: str = ""
    validate: Optional[Callable[[str], Any]] = None
    revise: Optional[Callable[[str, Any], str]] = None


class AgentStrategy(Protocol):
    pattern: str

    def run(self, ctx: AgentContext) -> AgentRunResult: ...
