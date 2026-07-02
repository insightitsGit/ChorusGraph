"""Finance agent handlers — unified Agent + AgentNode."""

from __future__ import annotations

from typing import Any, Dict, List

from chorusgraph.agents.agent import Agent
from chorusgraph.agents.agent_node import AgentNode, agent_result_to_state
from chorusgraph.agents.policy import PlanPolicy, PlanSolveOpts, ReActOpts, ReflectionOpts
from chorusgraph.agents.reflection import ValidationVerdict, run_reflection
from chorusgraph.agents.strategies.base import AgentRunResult
from chorusgraph.examples.finance_agent.nodes import (
    _future_value_in_text,
    _rate_in_text,
    make_cache_gate_handler,
    make_writer_handler,
    seed_fx_cache_from_tool_calls,
)
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime
from chorusgraph.nodes.roles import ResearcherNode, ValidatorNode
from chorusgraph.transforms.templates import try_template_draft


def _trace_dicts(trace) -> List[Dict[str, Any]]:
    return [s.to_dict() if hasattr(s, "to_dict") else dict(s) for s in trace]


def _rule_chain_from_trace(trace) -> List[str]:
    rules = []
    for step in trace:
        if hasattr(step, "to_rule"):
            rules.append(step.to_rule())
        elif isinstance(step, dict):
            rules.append(f"{step.get('kind')}={step.get('content', '')[:240]}")
    return rules


def _react_cache_seed_mapper(
    runtime: FinanceRuntime,
    state: Dict[str, Any],
    result: AgentRunResult,
) -> Dict[str, Any]:
    if state.get("cache_hit"):
        return {}
    seed_fx_cache_from_tool_calls(
        runtime,
        state.get("message") or "",
        result.tool_calls,
        extra_queries=list(state.get("cache_seed_phrases") or []),
    )
    return {}


def make_react_agent_handler(runtime: FinanceRuntime, *, policy: PlanPolicy | None = None):
    """Legacy handler — prefer AgentNode."""
    policy = policy or PlanPolicy(max_steps=6)
    agent = Agent(
        pattern="react",
        tools=runtime.tool_registry,
        model=runtime.ensure_gemini().generate_json,
        role=ResearcherNode("react_agent").role,
        policy=policy,
        pattern_opts=ReActOpts(max_tool_calls=policy.max_steps),
    )
    node = AgentNode(
        agent,
        node_id="react_agent",
        state_mapper=lambda state, result: _react_cache_seed_mapper(runtime, state, result),
    )
    return node.handler


def make_plan_solve_handler(runtime: FinanceRuntime, *, policy: PlanPolicy | None = None):
    policy = policy or PlanPolicy(max_steps=10)
    agent = Agent(
        pattern="plan_solve",
        tools=runtime.tool_registry,
        model=runtime.ensure_gemini().generate_json,
        policy=policy,
        pattern_opts=PlanSolveOpts(max_plan_steps=policy.max_steps, on_step_failure="abort"),
    )
    node = AgentNode(agent, node_id="plan_solve")
    return node.handler


def make_pattern_writer_handler(runtime: FinanceRuntime):
    """Unified writer — template/ONNX path handles single and multi-tool results."""
    return make_writer_handler(runtime)


def make_reflection_validator_handler(runtime: FinanceRuntime, *, policy: PlanPolicy | None = None):
    policy = policy or PlanPolicy(max_reflection_passes=3)
    role_node = ValidatorNode("validator")

    def validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
        draft = state.get("draft_response") or ""
        tool_results = state.get("tool_results") or []
        tool_result = state.get("tool_result") or {}
        all_rates = []
        all_fvs = []
        for obs in tool_results:
            if isinstance(obs, dict) and "rate" in obs:
                all_rates.append(float(obs["rate"]))
            if isinstance(obs, dict) and "future_value" in obs:
                all_fvs.append(float(obs["future_value"]))
        if tool_result and "rate" in tool_result:
            all_rates.append(float(tool_result["rate"]))
        if tool_result and "future_value" in tool_result:
            all_fvs.append(float(tool_result["future_value"]))

        initial_draft = draft
        if state.get("reflection_demo_wrong_figure"):
            initial_draft = "The USD/EUR rate is 0.9900 (incorrect). Other rates may also be wrong."

        def validate(text: str) -> ValidationVerdict:
            notes: List[str] = []
            approved = True
            for rate in all_rates:
                if not _rate_in_text(rate, text):
                    notes.append(f"Draft missing rate {rate}")
                    approved = False
            for fv in all_fvs:
                if not _future_value_in_text(fv, text):
                    notes.append(f"Draft missing future value {fv}")
                    approved = False
            if not approved and not notes:
                notes.append("validator rejected draft")
            return ValidationVerdict(approved=approved, notes=notes)

        def revise(text: str, verdict: ValidationVerdict) -> str:
            rewritten = try_template_draft(
                message=state.get("message") or "",
                tool_result=tool_result if tool_result else None,
                tool_results=tool_results,
            )
            if rewritten:
                if all_rates and all(_rate_in_text(r, rewritten) for r in all_rates):
                    return rewritten
                if all_fvs and all(_future_value_in_text(fv, rewritten) for fv in all_fvs):
                    return rewritten
                for rate in all_rates:
                    if _rate_in_text(rate, rewritten):
                        return rewritten
            gemini = runtime.ensure_gemini()
            system = role_node.role.system_prompt if role_node.role else ""
            user = (
                f"Draft:\n{text}\n\nTool data:\n{tool_results or tool_result}\n\n"
                f"Validation notes: {verdict.notes}\n"
                "Rewrite with exact rates from tool data. One concise paragraph."
            )
            return gemini.generate(system, user)

        reflection = run_reflection(
            initial_draft=initial_draft if state.get("reflection_demo_wrong_figure") else draft,
            validate=validate,
            revise=revise,
            policy=policy,
            pattern_opts=ReflectionOpts(max_revisions=policy.max_reflection_passes),
        )

        message = state.get("message") or ""
        history = list(state.get("conversation_history") or [])
        if message:
            history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": reflection.draft})

        return {
            "validation": reflection.validation,
            "response": reflection.draft,
            "conversation_history": history,
            "agent_trace": _trace_dicts(reflection.trace),
            "rule_chain": _rule_chain_from_trace(reflection.trace) + [f"validator approved={reflection.approved}"],
            "reflection_pass": reflection.passes,
        }

    return role_node.bind(validator_node)


def build_react_agent(runtime: FinanceRuntime, *, policy: PlanPolicy | None = None) -> Agent:
    policy = policy or PlanPolicy(max_steps=6)
    return Agent(
        pattern="react",
        tools=runtime.tool_registry,
        model=runtime.ensure_gemini().generate_json,
        role=ResearcherNode("react_agent").role,
        policy=policy,
        pattern_opts=ReActOpts(max_tool_calls=policy.max_steps),
    )


def make_agent_node_from_runtime(runtime: FinanceRuntime, *, node_id: str = "react_agent") -> AgentNode:
    """Demonstrate Agent IS-A Node in the finance graph."""
    agent = build_react_agent(runtime)
    return AgentNode(agent, node_id=node_id)
