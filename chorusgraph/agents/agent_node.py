"""AgentNode — Agent IS-A Node (DESIGN §7.7)."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from chorusgraph.agents.agent import Agent
from chorusgraph.agents.strategies.base import AgentRunResult
from chorusgraph.nodes.roles import Node, RoleTemplate, promote


def _trace_dicts(result: AgentRunResult) -> List[Dict[str, Any]]:
    return [s.to_dict() for s in result.trace]


def _rule_chain_from_result(result: AgentRunResult) -> List[str]:
    return [s.to_rule() for s in result.trace]


def agent_result_to_state(result: AgentRunResult, *, pattern: str, prior: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    prior = prior or {}
    tool_results = [obs for obs in result.observations if isinstance(obs, dict) and "rate" in obs]
    if not tool_results and result.observations:
        tool_results = [
            (obs.get("data") if isinstance(obs, dict) else obs) for obs in result.observations
        ]
    update: Dict[str, Any] = {
        "tool_calls": list(prior.get("tool_calls") or []) + result.tool_calls,
        "tool_results": tool_results,
        "tool_result": tool_results[-1] if tool_results else None,
        "needs_tool": False,
        "agent_trace": _trace_dicts(result),
        "rule_chain": _rule_chain_from_result(result),
    }
    if pattern == "react":
        update["research_plan"] = "ReAct via Agent"
    if pattern == "plan_solve":
        update["plan_steps"] = [
            {"id": s.id, "description": s.description, "tool": s.tool} for s in result.plan
        ]
    if pattern == "reflection":
        update["validation"] = result.validation
        update["response"] = result.draft
        update["draft_response"] = result.draft
        update["reflection_pass"] = result.passes
    return update


def AgentNode(
    agent: Agent,
    node_id: str = "agent",
    *,
    state_mapper: Optional[Callable[[Dict[str, Any], AgentRunResult], Dict[str, Any]]] = None,
) -> Node:
    """Wrap an Agent as a LangGraph-compatible Node."""

    def handler(state: Dict[str, Any]) -> Dict[str, Any]:
        if state.get("cache_hit") and state.get("tool_result") and agent.pattern == "react":
            return {"agent_trace": [], "rule_chain": ["agent=skipped_cache_hit"]}
        message = state.get("message") or ""
        kwargs: Dict[str, Any] = {}
        if agent.pattern == "reflection":
            kwargs["initial_draft"] = state.get("draft_response") or ""
            if state.get("_reflection_validate"):
                kwargs["validate"] = state["_reflection_validate"]
            if state.get("_reflection_revise"):
                kwargs["revise"] = state["_reflection_revise"]
        result = agent.run(message, **kwargs)
        update = agent_result_to_state(result, pattern=agent.pattern, prior=state)
        if state_mapper:
            update = state_mapper(state, result) | update
        return update

    role = agent.role
    node = Node(node_id=node_id, role=role, handler=handler)
    return node


def promote_to_agent(node: Node, agent: Agent) -> Node:
    """Promote a plain Node to an Agent-backed node."""
    bound = AgentNode(agent, node_id=node.node_id)
    return Node(node_id=node.node_id, role=agent.role or node.role, handler=bound.handler)
