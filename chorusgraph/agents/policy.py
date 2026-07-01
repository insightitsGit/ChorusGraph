"""PlanPolicy, pattern options, and LATER belief-tier stubs (DESIGN §7.5, §7.8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


OnExhaust = Literal["best_effort", "abstain", "escalate"]
TraceLevel = Literal["minimal", "normal", "verbose"]
StepFailureAction = Literal["retry", "skip", "abort", "replan"]
ReflectionEvaluator = Literal["llm_critique", "run_tests", "grounding_guard"]


class BeliefPolicyNotCalibratedError(RuntimeError):
    """Raised when a LATER belief-tier knob is enabled before A/B calibration."""


@dataclass(frozen=True)
class BeliefPolicy:
    """
    LATER tier — API surface only. Behavior disabled until A/B-calibrated signals (§7.5).

    Any non-None value raises BeliefPolicyNotCalibratedError at Agent.run() time.
    """

    confidence_stop: Optional[float] = None
    groundedness_floor: Optional[float] = None
    memory_confidence_gate: Optional[float] = None
    escalation_policy: Optional[str] = None
    novelty_adaptive_steps: Optional[bool] = None

    def assert_disabled(self) -> None:
        enabled = {
            k: v
            for k, v in (
                ("confidence_stop", self.confidence_stop),
                ("groundedness_floor", self.groundedness_floor),
                ("memory_confidence_gate", self.memory_confidence_gate),
                ("escalation_policy", self.escalation_policy),
                ("novelty_adaptive_steps", self.novelty_adaptive_steps),
            )
            if v is not None
        }
        if enabled:
            raise BeliefPolicyNotCalibratedError(
                "Belief-tier knobs require A/B-calibrated grounding/confidence signals (§7.5). "
                f"Disabled until calibration. Enabled knobs: {list(enabled.keys())}"
            )


@dataclass(frozen=True)
class PlanPolicy:
    """Shared agent budgets and trace controls."""

    max_steps: int = 8
    token_budget: int = 8000
    max_reflection_passes: int = 3
    on_exhaust: OnExhaust = "best_effort"
    trace_level: TraceLevel = "normal"

    def steps_remaining(self, used: int) -> int:
        return max(0, self.max_steps - used)

    def within_budget(self, tokens_used: int) -> bool:
        return tokens_used < self.token_budget


@dataclass(frozen=True)
class ReActOpts:
    max_tool_calls: int = 6
    require_tool_before_finish: bool = False
    stop_on_repeated_action: bool = False
    observation_char_limit: int = 2000


@dataclass(frozen=True)
class ReflectionOpts:
    max_revisions: int = 3
    critic_model: Optional[str] = None
    evaluator: ReflectionEvaluator = "grounding_guard"
    stop_when_no_improvement: bool = False


@dataclass(frozen=True)
class PlanSolveOpts:
    max_plan_steps: int = 10
    replan_on_failure: bool = False
    on_step_failure: StepFailureAction = "abort"
    checkpoint_after_step: bool = False
    validate_plan: bool = True


PatternOpts = ReActOpts | ReflectionOpts | PlanSolveOpts

PATTERN_DEFAULTS: dict[str, object] = {
    "react": ReActOpts(),
    "reflection": ReflectionOpts(),
    "plan_solve": PlanSolveOpts(),
}
