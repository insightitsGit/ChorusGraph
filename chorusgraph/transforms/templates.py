"""Deterministic response templates — no LLM on the hot path when data is complete."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from chorusgraph.memory.structured_recall import StructuredRecallContext


def _fx_line(tool_result: Dict[str, Any]) -> Optional[str]:
    rate = tool_result.get("rate")
    if rate is None:
        return None
    from_c = tool_result.get("from_currency") or tool_result.get("from") or "USD"
    to_c = tool_result.get("to_currency") or tool_result.get("to") or "EUR"
    date = tool_result.get("date") or ""
    date_part = f" (as of {date})" if date else ""
    return f"The exchange rate is 1 {from_c} = {rate} {to_c}{date_part}."


def template_fx_response(tool_result: Dict[str, Any]) -> Optional[str]:
    return _fx_line(tool_result)


def template_multi_fx_response(tool_results: List[Any]) -> Optional[str]:
    lines: List[str] = []
    for item in tool_results:
        if isinstance(item, dict) and item.get("rate") is not None:
            line = _fx_line(item)
            if line:
                lines.append(line)
    if not lines:
        return None
    if len(lines) == 1:
        return lines[0]
    return "\n".join(lines)


def format_evidence_block(ctx: "StructuredRecallContext", *, max_facts: int = 8) -> str:
    """Structured memory facts for the rare LLM fallback — not prose recall."""
    lines = []
    for item in ctx.evidence[:max_facts]:
        fact = item.get("fact") or ""
        if not fact:
            continue
        conf = float(item.get("confidence") or 0.0)
        lines.append(f"- {fact} (confidence={conf:.3f})")
    if not lines:
        return ""
    return "Known facts from memory (authoritative):\n" + "\n".join(lines)


def _memory_prefix(ctx: Optional["StructuredRecallContext"]) -> str:
    if ctx is None or not ctx.evidence:
        return ""
    facts = [e.get("fact", "") for e in ctx.evidence if e.get("fact")]
    if not facts:
        return ""
    return "Based on your profile: " + "; ".join(facts) + "\n\n"


def try_template_draft(
    *,
    message: str,
    tool_result: Optional[Dict[str, Any]] = None,
    tool_results: Optional[List[Any]] = None,
    memory_ctx: Optional["StructuredRecallContext"] = None,
) -> Optional[str]:
    """
    Build a draft without LLM when tool payloads (and optional memory facts) suffice.

    Returns None when the question needs generative synthesis (e.g. allocation advice).
    """
    _ = message  # reserved for future intent gating
    tool_results = tool_results or []
    prefix = _memory_prefix(memory_ctx)

    if tool_results:
        body = template_multi_fx_response(tool_results)
        if body:
            return prefix + body

    if tool_result and tool_result.get("rate") is not None:
        body = template_fx_response(tool_result)
        if body:
            return prefix + body

    return None
