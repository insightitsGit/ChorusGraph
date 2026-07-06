"""Plan-Solve strategy — static planner + sequential executor."""

from __future__ import annotations

import json
from typing import Any, List

from chorusgraph.agents.loop import AgentTraceStep, TraceKind
from chorusgraph.agents.plan_utils import PlanStep, _try_compute_cross, plan_tasks
from chorusgraph.agents.policy import PlanSolveOpts
from chorusgraph.agents.strategies.base import AgentContext, AgentRunResult


class PlanSolveStrategy:
    pattern = "plan_solve"

    def run(self, ctx: AgentContext) -> AgentRunResult:
        ctx.belief.assert_disabled()
        opts = ctx.pattern_opts if isinstance(ctx.pattern_opts, PlanSolveOpts) else PlanSolveOpts()
        trace: List[AgentTraceStep] = []
        observations: List[Any] = []
        tool_calls: List[dict] = []

        trace.append(AgentTraceStep(TraceKind.THOUGHT, "planner: emit static task list"))
        plan = plan_tasks(question=ctx.question, registry=ctx.registry, llm_json=ctx.llm_json)

        if opts.validate_plan:
            for step in plan:
                if step.tool and step.tool not in ctx.registry.names():
                    trace.append(
                        AgentTraceStep(
                            TraceKind.OBSERVATION,
                            f"invalid plan tool: {step.tool}",
                            metadata={"step_id": step.id},
                        )
                    )

        limit = min(opts.max_plan_steps, ctx.policy.max_steps)
        for step in plan[:limit]:
            trace.append(
                AgentTraceStep(
                    TraceKind.PLAN_STEP,
                    f"{step.id}. {step.description} → {step.tool}({step.args})",
                    metadata={"step_id": step.id, "tool": step.tool, "args": step.args},
                )
            )

        failed_step = None
        step_index = 0
        while step_index < len(plan) and step_index < limit:
            step = plan[step_index]
            if not (step.tool or "").strip():
                cross = _try_compute_cross(step.description, observations)
                if cross is not None:
                    observations.append({"step_id": step.id, "data": cross, "computed": True})
                    trace.append(
                        AgentTraceStep(
                            TraceKind.OBSERVATION,
                            str(cross)[:2000],
                            metadata={"step_id": step.id, "computed": True},
                        )
                    )
                else:
                    trace.append(
                        AgentTraceStep(
                            TraceKind.OBSERVATION,
                            f"skipped non-tool step: {step.description}",
                            metadata={"step_id": step.id},
                        )
                    )
                if opts.checkpoint_after_step:
                    trace.append(
                        AgentTraceStep(
                            TraceKind.ROUTER,
                            f"checkpoint after step {step.id}",
                            metadata={"checkpoint": True, "step_id": step.id},
                        )
                    )
                step_index += 1
                continue

            trace.append(
                AgentTraceStep(
                    TraceKind.ACTION,
                    f"execute step {step.id}: {step.tool}",
                    metadata={"step_id": step.id},
                )
            )
            result = ctx.registry.run(step.tool, **step.args)
            tool_calls.append(result.to_state_dict())

            if result.ok:
                observations.append({"step_id": step.id, "data": result.data})
                trace.append(
                    AgentTraceStep(
                        TraceKind.OBSERVATION,
                        str(result.data)[:2000],
                        metadata={"step_id": step.id},
                    )
                )
                if opts.checkpoint_after_step:
                    trace.append(
                        AgentTraceStep(
                            TraceKind.ROUTER,
                            f"checkpoint after step {step.id}",
                            metadata={"checkpoint": True, "step_id": step.id},
                        )
                    )
                step_index += 1
                continue

            trace.append(
                AgentTraceStep(
                    TraceKind.OBSERVATION,
                    f"ERROR: {result.error}",
                    metadata={"step_id": step.id},
                )
            )
            action = opts.on_step_failure
            if action == "skip":
                step_index += 1
                continue
            if action == "retry":
                continue
            if action == "replan" and opts.replan_on_failure:
                trace.append(AgentTraceStep(TraceKind.THOUGHT, "replan after failure"))
                plan = plan_tasks(question=ctx.question, registry=ctx.registry, llm_json=ctx.llm_json)
                step_index = 0
                continue
            failed_step = step.id
            break

        return AgentRunResult(
            trace=trace,
            observations=observations,
            tool_calls=tool_calls,
            plan=plan,
            failed_step=failed_step,
            finished=failed_step is None,
            finish_reason=None if failed_step is None else "step_failure",
        )
