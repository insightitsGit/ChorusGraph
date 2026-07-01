"""Reflection strategy — generate → critique → revise."""

from __future__ import annotations

from chorusgraph.agents.loop import AgentTraceStep, TraceKind
from chorusgraph.agents.policy import ReflectionOpts
from chorusgraph.agents.reflection import ValidationVerdict
from chorusgraph.agents.strategies.base import AgentContext, AgentRunResult


class ReflectionStrategy:
    pattern = "reflection"

    def run(self, ctx: AgentContext) -> AgentRunResult:
        ctx.belief.assert_disabled()
        if ctx.validate is None or ctx.revise is None:
            raise ValueError("Reflection pattern requires validate and revise callbacks")

        opts = ctx.pattern_opts if isinstance(ctx.pattern_opts, ReflectionOpts) else ReflectionOpts()
        max_passes = min(opts.max_revisions, ctx.policy.max_reflection_passes)
        trace: list[AgentTraceStep] = []
        draft = ctx.initial_draft

        for attempt in range(max_passes):
            trace.append(AgentTraceStep(TraceKind.THOUGHT, f"validation pass {attempt + 1}"))
            verdict = ctx.validate(draft)
            if not isinstance(verdict, ValidationVerdict):
                verdict = ValidationVerdict(
                    approved=bool(getattr(verdict, "approved", False)),
                    notes=list(getattr(verdict, "notes", []) or []),
                )
            trace.append(
                AgentTraceStep(
                    TraceKind.OBSERVATION,
                    f"approved={verdict.approved}; notes={'; '.join(verdict.notes)}",
                    metadata={"approved": verdict.approved, "notes": verdict.notes, "evaluator": opts.evaluator},
                )
            )
            if verdict.approved:
                return AgentRunResult(
                    draft=draft,
                    approved=True,
                    trace=trace,
                    passes=attempt + 1,
                    validation={"approved": True, "notes": verdict.notes, "passes": attempt + 1},
                    finished=True,
                )
            revised = ctx.revise(draft, verdict)
            trace.append(AgentTraceStep(TraceKind.REVISION, revised[:500], metadata={"pass": attempt + 1}))
            if opts.stop_when_no_improvement and revised.strip() == draft.strip():
                break
            draft = revised

        final = ctx.validate(draft)
        if not isinstance(final, ValidationVerdict):
            final = ValidationVerdict(approved=bool(getattr(final, "approved", False)), notes=[])
        return AgentRunResult(
            draft=draft,
            approved=final.approved,
            trace=trace,
            passes=max_passes,
            validation={"approved": final.approved, "notes": final.notes, "passes": max_passes},
            finished=True,
        )
