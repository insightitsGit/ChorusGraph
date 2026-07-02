"""Finance agent graph node handlers."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from chorusgraph.cache_gate import gate
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime
from chorusgraph.memory.recall import format_evidence_for_llm
from chorusgraph.nodes.roles import ResearcherNode, ValidatorNode, WriterNode
from chorusgraph.transforms.intent import needs_compound_tool, parse_compound_params
from chorusgraph.transforms.projector import project_text
from chorusgraph.transforms.templates import try_template_draft
from chorusgraph.sections.models import CachePolicy, Section

_CURRENCY_RE = re.compile(r"\b([A-Z]{3})\b")
_FX_HINTS = ("exchange rate", "convert", "fx", "currency", "usd", "eur", "gbp", "jpy")


def _rate_in_text(rate: float, text: str) -> bool:
    if str(rate) in text:
        return True
    for decimals in (2, 3, 4, 5, 6):
        formatted = f"{rate:.{decimals}f}"
        if formatted in text or formatted.rstrip("0").rstrip(".") in text:
            return True
    nums = re.findall(r"\d+\.\d+", text)
    return any(abs(float(n) - rate) < 1e-4 for n in nums)


def _future_value_in_text(fv: float, text: str, *, tol: float = 1.0) -> bool:
    for match in re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.\d+", text):
        val = float(match.replace(",", ""))
        if abs(val - fv) <= tol:
            return True
    return False


def _parse_fx_pair(message: str) -> Optional[Tuple[str, str]]:
    upper = message.upper()
    codes = _CURRENCY_RE.findall(upper)
    # filter common false positives
    valid = [c for c in codes if c in {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "INR"}]
    if len(valid) >= 2:
        return valid[0], valid[1]
    lower = message.lower()
    if "usd" in lower and "eur" in lower:
        return "USD", "EUR"
    if "usd" in lower and "gbp" in lower:
        return "USD", "GBP"
    if "eur" in lower and "gbp" in lower:
        return "EUR", "GBP"
    if any(h in lower for h in _FX_HINTS) and len(valid) == 1:
        other = "USD" if valid[0] != "USD" else "EUR"
        return "USD", valid[0] if valid[0] != "USD" else "EUR"
    return None


def _needs_fx_tool(message: str) -> bool:
    lower = message.lower()
    return any(h in lower for h in _FX_HINTS) or _parse_fx_pair(message) is not None


def make_cache_gate_handler(
    runtime: FinanceRuntime,
    *,
    coarse_threshold: float = 0.82,
    verify_threshold: float = 0.85,
):
    def cache_gate_node(state: Dict[str, Any]) -> Dict[str, Any]:
        message = state.get("message") or ""
        section = Section(
            section_id="fx_lookup",
            category_slug="fx_rates",
            content=message,
            cache_policy=CachePolicy.REPLAY_SAFE,
        )
        decision = gate(
            message,
            section,
            runtime.cache,
            runtime.sidecar,
            coarse_threshold=coarse_threshold,
            verify_threshold=verify_threshold,
        )
        update: Dict[str, Any] = {
            "cache_hit": decision.is_hit,
            "cache_score": decision.verify_score or decision.coarse_score,
            "cache_decision": decision.kind.value,
            "rule_chain": [f"cache_gate={decision.kind.value}"],
        }
        if decision.is_hit and decision.value:
            update["tool_result"] = decision.value
            update["needs_tool"] = False
            update["tool_skipped_reason"] = "cache_gate_hit"
        return update

    return cache_gate_node


def make_researcher_handler(runtime: FinanceRuntime):
    role_node = ResearcherNode("researcher")

    def researcher_node(state: Dict[str, Any]) -> Dict[str, Any]:
        if state.get("cache_hit") and state.get("tool_result"):
            return {
                "needs_tool": False,
                "research_plan": "Use cached FX data from cache_gate.",
                "rule_chain": ["researcher=cache_hit_skip_tool"],
            }

        message = state.get("message") or ""
        history = state.get("conversation_history") or []

        pair = _parse_fx_pair(message)
        context_msg = message
        if pair is None and history and any(
            w in message.lower() for w in ("what about", "and ", "also", "how about")
        ):
            last_user = next(
                (m["content"] for m in reversed(history) if m.get("role") == "user"),
                "",
            )
            context_msg = f"{last_user} {message}"
            pair = _parse_fx_pair(context_msg)

        compound_args = parse_compound_params(message)
        if compound_args:
            return {
                "needs_tool": True,
                "tool_name": "compound_interest",
                "tool_args": compound_args,
                "research_plan": "Compute FV via deterministic compound_interest tool.",
                "rule_chain": ["researcher=compound_interest"],
            }

        if _needs_fx_tool(context_msg) and pair and not needs_compound_tool(message):
            from_c, to_c = pair
            return {
                "needs_tool": True,
                "tool_name": "fetch_exchange_rate",
                "tool_args": {"from_currency": from_c, "to_currency": to_c},
                "research_plan": f"Fetch live {from_c}/{to_c} via Frankfurter.",
                "rule_chain": [f"researcher=fx_pair {from_c}/{to_c}"],
            }

        return {
            "needs_tool": False,
            "research_plan": "No live tool required.",
            "rule_chain": ["researcher=no_tool"],
        }

    return role_node.bind(researcher_node)


def make_tool_handler(runtime: FinanceRuntime):
    def tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
        if not state.get("needs_tool"):
            return {"rule_chain": ["tool=skipped"]}
        name = state.get("tool_name") or "fetch_exchange_rate"
        args = dict(state.get("tool_args") or {})
        result = runtime.tool_registry.run(name, **args)
        tool_calls = list(state.get("tool_calls") or [])
        tool_calls.append(result.to_state_dict())
        update: Dict[str, Any] = {
            "tool_result": result.data if result.ok else None,
            "tool_error": result.error,
            "tool_calls": tool_calls,
            "rule_chain": [f"tool={name} ok={result.ok}"],
        }
        if result.ok and result.data and name == "fetch_exchange_rate":
            message = state.get("message") or ""
            pair = f"{args.get('from_currency', '')}/{args.get('to_currency', '')}"
            runtime.seed_tool_cache(message or pair, result.data)
        return update

    return tool_node


def make_compound_tool_handler(runtime: FinanceRuntime):
    """Deterministic compound path — CPU tool, no ReAct/LLM."""

    def compound_tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
        message = state.get("message") or ""
        params = parse_compound_params(message)
        if not params:
            return {
                "needs_tool": False,
                "rule_chain": ["compound_tool=parse_failed"],
            }
        result = runtime.tool_registry.run("compound_interest", **params)
        tool_calls = list(state.get("tool_calls") or [])
        tool_calls.append(result.to_state_dict())
        return {
            "tool_result": result.data if result.ok else None,
            "tool_error": result.error,
            "tool_calls": tool_calls,
            "needs_tool": False,
            "rule_chain": [f"compound_tool ok={result.ok}"],
        }

    return compound_tool_node


def make_writer_handler(runtime: FinanceRuntime):
    role_node = WriterNode("writer")

    def writer_node(state: Dict[str, Any]) -> Dict[str, Any]:
        message = state.get("message") or ""
        history = state.get("conversation_history") or []
        tool_result = state.get("tool_result")
        tool_results = state.get("tool_results") or []
        system = role_node.role.system_prompt if role_node.role else ""

        prism_update: Dict[str, Any] = {}
        if runtime.cache is not None and message:
            _, envelope = project_text(runtime.cache, message)
            prism_update["prism_sequence"] = [envelope]

        memory_ctx = (
            runtime.cortex.recall_structured(message, cache=runtime.cache)
            if runtime.cortex
            else None
        )

        draft = try_template_draft(
            message=message,
            tool_result=tool_result,
            tool_results=tool_results,
            memory_ctx=memory_ctx,
        )
        used_llm = False
        if draft is None:
            used_llm = True
            gemini = runtime.ensure_gemini()
            context_parts = [f"User question: {message}"]
            if memory_ctx:
                block = format_evidence_for_llm(memory_ctx)
                if block:
                    context_parts.append(block)
            if tool_results:
                context_parts.append(f"Tool observations (authoritative): {tool_results}")
            elif tool_result:
                context_parts.append(f"Tool data (authoritative): {tool_result}")
            elif state.get("tool_error"):
                context_parts.append(f"Tool error: {state['tool_error']}")
            user = "\n".join(context_parts)
            draft = gemini.generate(system, user, history=history)

        update: Dict[str, Any] = {
            "draft_response": draft,
            "rule_chain": ["writer=gemini_draft"] if used_llm else ["writer=template_draft"],
            **prism_update,
        }
        if memory_ctx:
            update.update(memory_ctx.to_memory_state())
            update["rule_chain"] = list(update["rule_chain"]) + [
                f"memory_confidence={memory_ctx.confidence:.3f}",
                f"memory_vector_dim={len(memory_ctx.query_vector_64)}",
            ]
        return update

    return role_node.bind(writer_node)


def make_validator_handler(runtime: FinanceRuntime):
    role_node = ValidatorNode("validator")

    def validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
        draft = state.get("draft_response") or ""
        tool_result = state.get("tool_result") or {}
        approved = True
        notes: List[str] = []

        if tool_result and "rate" in tool_result:
            rate = float(tool_result["rate"])
            if not _rate_in_text(rate, draft):
                notes.append(f"Draft missing explicit rate {rate}")
                approved = False

        if tool_result and "future_value" in tool_result:
            fv = float(tool_result["future_value"])
            if not _future_value_in_text(fv, draft):
                notes.append(f"Draft missing future value {fv}")
                approved = False

        if not approved:
            rewritten = try_template_draft(
                message=state.get("message") or "",
                tool_result=tool_result if tool_result else None,
            )
            if rewritten and tool_result and "rate" in tool_result:
                draft = rewritten
                if _rate_in_text(float(tool_result.get("rate", 0)), draft):
                    approved = True
                    notes.append("validator=template_rewrite_ok")
            elif rewritten and tool_result and "future_value" in tool_result:
                draft = rewritten
                if _future_value_in_text(float(tool_result.get("future_value", 0)), draft):
                    approved = True
                    notes.append("validator=compound_template_rewrite_ok")
            if not approved:
                gemini = runtime.ensure_gemini()
                system = role_node.role.system_prompt if role_node.role else ""
                user = (
                    f"Draft:\n{draft}\n\nTool data:\n{tool_result}\n\n"
                    "Rewrite the draft to include the exact tool rate. One short paragraph."
                )
                draft = gemini.generate(system, user)
                if tool_result and "rate" in tool_result and _rate_in_text(
                    float(tool_result.get("rate", 0)), draft
                ):
                    approved = True
                    notes.append("validator=gemini_rewrite_ok")
                elif tool_result and "future_value" in tool_result and _future_value_in_text(
                    float(tool_result.get("future_value", 0)), draft
                ):
                    approved = True
                    notes.append("validator=compound_gemini_rewrite_ok")
                else:
                    notes.append("validator=rewrite_still_missing_rate")

        validation = {
            "approved": approved,
            "notes": notes,
            "role": "validator",
        }
        message = state.get("message") or ""
        history = list(state.get("conversation_history") or [])
        if message:
            history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": draft})
        return {
            "validation": validation,
            "response": draft,
            "conversation_history": history,
            "rule_chain": [f"validator approved={approved}"],
        }

    return role_node.bind(validator_node)


def route_after_cache(state: Dict[str, Any]) -> str:
    if state.get("cache_hit") and state.get("tool_result"):
        return "writer"
    return "researcher"


def route_after_cache_pattern(state: Dict[str, Any]) -> str:
    """B graph: cache hit → writer; compound intent → CPU tool; else ReAct."""
    if state.get("cache_hit") and state.get("tool_result"):
        return "writer"
    if parse_compound_params(state.get("message") or ""):
        return "compound_tool"
    return "react_agent"


def route_after_research(state: Dict[str, Any]) -> str:
    return "tool" if state.get("needs_tool") else "writer"
