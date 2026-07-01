"""ReAct strategy — Thought → Action → Observation."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Set, Tuple

from chorusgraph.agents.loop import LoopOutcome, run_agent_loop
from chorusgraph.agents.policy import ReActOpts
from chorusgraph.agents.react_utils import parse_react_json, tool_catalog
from chorusgraph.agents.strategies.base import AgentContext, AgentRunResult


REACT_SYSTEM = """You are a finance ReAct agent. Decide which tools to call to answer the user question.

Available tools (JSON schema):
{tool_catalog}

Respond with JSON ONLY:
{{
  "thought": "<your reasoning>",
  "action": {{"tool": "<tool_name>", "args": {{...}}}} | null,
  "finish": true | false
}}

Rules:
- Set finish=true ONLY when you have enough tool observations to answer fully.
- For comparisons needing multiple rates, call fetch_exchange_rate once per pair.
- Use exact tool names from the catalog.
- args must match tool parameter names exactly.
"""


class ReactStrategy:
    pattern = "react"

    def run(self, ctx: AgentContext) -> AgentRunResult:
        ctx.belief.assert_disabled()
        opts = ctx.pattern_opts if isinstance(ctx.pattern_opts, ReActOpts) else ReActOpts()
        catalog = tool_catalog(ctx.registry)
        system = REACT_SYSTEM.format(tool_catalog=catalog)
        tool_calls: List[Dict[str, Any]] = []
        seen_actions: Set[Tuple[str, str]] = set()
        tool_call_count = 0
        forced_finish = False
        finish_reason_override: str | None = None
        block_finish_no_tool = False

        def _action_key(action: Dict[str, Any]) -> Tuple[str, str]:
            tool = action.get("tool") or action.get("name") or ""
            args = action.get("args") or action.get("arguments") or {}
            return tool, json.dumps(args, sort_keys=True)

        def _truncate(obs: Any) -> Any:
            text = obs if isinstance(obs, str) else str(obs)
            if len(text) > opts.observation_char_limit:
                return text[: opts.observation_char_limit] + "…"
            return obs

        def reason(*, scratchpad: str, step: int) -> Dict[str, Any]:
            nonlocal block_finish_no_tool, forced_finish, finish_reason_override
            if forced_finish:
                return {
                    "thought": "stopped by policy",
                    "finish": True,
                    "finish_reason": finish_reason_override,
                }
            user = f"Question: {ctx.question}\n\nScratchpad:\n{ctx.scratchpad_prefix}{scratchpad or '(empty)'}"
            raw = ctx.llm_json(system, user)
            parsed = parse_react_json(raw)
            finish = bool(parsed.get("finish"))
            if block_finish_no_tool:
                block_finish_no_tool = False
                finish = False
            return {
                "thought": parsed.get("thought") or "",
                "action": parsed.get("action"),
                "finish": finish,
                "tokens_used": len(raw) // 4,
            }

        def act(action: Dict[str, Any]) -> Any:
            nonlocal tool_call_count, forced_finish, finish_reason_override
            if tool_call_count >= opts.max_tool_calls:
                forced_finish = True
                finish_reason_override = "max_tool_calls"
                return "ERROR: max_tool_calls reached"
            key = _action_key(action)
            if opts.stop_on_repeated_action and key in seen_actions:
                forced_finish = True
                finish_reason_override = "repeated_action"
                return "ERROR: repeated action blocked"
            seen_actions.add(key)

            tool = action.get("tool") or action.get("name")
            args = dict(action.get("args") or action.get("arguments") or {})
            result = ctx.registry.run(tool, **args)
            tool_calls.append(result.to_state_dict())
            tool_call_count += 1
            if result.ok:
                return _truncate(result.data)
            return _truncate(f"ERROR: {result.error}")

        def route(*, reason_result: Dict[str, Any], observations: List[Any]) -> str:
            nonlocal block_finish_no_tool, forced_finish
            if forced_finish:
                return "finish"
            wants_finish = bool(reason_result.get("finish"))
            action = reason_result.get("action")
            has_action = bool(action and (action.get("tool") or action.get("name")))

            if wants_finish:
                if opts.require_tool_before_finish and not tool_calls:
                    if has_action and tool_call_count < opts.max_tool_calls:
                        return "act"
                    block_finish_no_tool = True
                    return "continue"
                return "finish"
            if has_action:
                if tool_call_count >= opts.max_tool_calls:
                    return "finish"
                return "act"
            if observations:
                return "finish"
            return "finish"

        outcome: LoopOutcome = run_agent_loop(
            policy=ctx.policy,
            reason=reason,
            act=act,
            route=route,
            initial_scratchpad="",
        )

        return AgentRunResult(
            trace=outcome.trace,
            observations=outcome.observations,
            tool_calls=tool_calls,
            finished=outcome.finished,
            finish_reason=finish_reason_override or outcome.finish_reason,
        )
