"""Generic agent-loop substrate — reason ↔ act ↔ route with observable trace."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

from chorusgraph.agents.policy import PlanPolicy


class TraceKind(str, Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    PLAN_STEP = "plan_step"
    REVISION = "revision"
    ROUTER = "router"


@dataclass
class AgentTraceStep:
    kind: TraceKind
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "content": self.content,
            "metadata": self.metadata,
        }

    def to_rule(self) -> str:
        return f"{self.kind.value}={self.content[:240]}"


@dataclass
class LoopOutcome:
    finished: bool
    trace: List[AgentTraceStep] = field(default_factory=list)
    observations: List[Any] = field(default_factory=list)
    tokens_used: int = 0
    steps_used: int = 0
    finish_reason: Optional[str] = None


class Reasoner(Protocol):
    def __call__(self, *, scratchpad: str, step: int) -> Dict[str, Any]: ...


class Actor(Protocol):
    def __call__(self, action: Dict[str, Any]) -> Any: ...


class Router(Protocol):
    def __call__(self, *, reason_result: Dict[str, Any], observations: List[Any]) -> str: ...


def run_agent_loop(
    *,
    policy: PlanPolicy,
    reason: Reasoner,
    act: Optional[Actor],
    route: Router,
    initial_scratchpad: str = "",
) -> LoopOutcome:
    """
    Generic cyclic machinery: llm (reason) ↔ tool (act) ↔ router (act-or-finish).

    Each cycle appends Thought / Action / Observation steps to the trace.
    """
    trace: List[AgentTraceStep] = []
    observations: List[Any] = []
    scratchpad = initial_scratchpad
    tokens_used = 0
    steps_used = 0
    finished = False
    finish_reason: Optional[str] = None

    while steps_used < policy.max_steps and policy.within_budget(tokens_used):
        reason_result = reason(scratchpad=scratchpad, step=steps_used)
        tokens_used += int(reason_result.get("tokens_used") or 0)

        thought = (reason_result.get("thought") or "").strip()
        if thought:
            trace.append(AgentTraceStep(TraceKind.THOUGHT, thought))

        decision = route(reason_result=reason_result, observations=observations)
        trace.append(AgentTraceStep(TraceKind.ROUTER, decision, metadata={"step": steps_used}))

        if decision == "finish":
            finished = True
            finish_reason = reason_result.get("finish_reason") or "router_finish"
            steps_used += 1
            break

        if decision == "continue":
            scratchpad += f"\nThought: {thought}\n(Policy: continuing — tool required before finish)\n"
            steps_used += 1
            continue

        if decision == "act" and act is not None:
            action = reason_result.get("action") or {}
            tool_name = action.get("tool") or action.get("name") or "unknown"
            trace.append(
                AgentTraceStep(
                    TraceKind.ACTION,
                    f"{tool_name}({action.get('args') or action.get('arguments') or {}})",
                    metadata={"tool": tool_name, "args": action.get("args") or action.get("arguments") or {}},
                )
            )
            observation = act(action)
            observations.append(observation)
            obs_text = observation if isinstance(observation, str) else str(observation)
            trace.append(AgentTraceStep(TraceKind.OBSERVATION, obs_text[:2000], metadata={"tool": tool_name}))
            scratchpad += f"\nThought: {thought}\nAction: {tool_name}\nObservation: {obs_text}\n"
        else:
            scratchpad += f"\nThought: {thought}\n"
            if reason_result.get("error"):
                trace.append(AgentTraceStep(TraceKind.OBSERVATION, str(reason_result["error"])))

        steps_used += 1

    if not finished and steps_used >= policy.max_steps:
        finish_reason = "max_steps"
    elif not finished and not policy.within_budget(tokens_used):
        finish_reason = "token_budget"

    return LoopOutcome(
        finished=finished or bool(observations),
        trace=trace,
        observations=observations,
        tokens_used=tokens_used,
        steps_used=steps_used,
        finish_reason=finish_reason,
    )
