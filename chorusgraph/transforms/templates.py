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


def template_compound_response(tool_result: Dict[str, Any]) -> Optional[str]:
    fv = tool_result.get("future_value")
    if fv is None:
        return None
    principal = float(tool_result.get("principal") or 0)
    rate = float(tool_result.get("annual_rate_pct") or 0)
    years = float(tool_result.get("years") or 0)
    n = int(tool_result.get("compounds_per_year") or 1)
    if n == 12:
        freq = "monthly"
    elif n == 4:
        freq = "quarterly"
    elif n == 365:
        freq = "daily"
    else:
        freq = f"{n} times per year"
    return (
        f"If you invest ${principal:,.0f} at {rate}% annual interest compounded {freq} "
        f"for {years:g} years, the future value will be ${float(fv):,.2f}."
    )


def _compound_line(item: Dict[str, Any]) -> Optional[str]:
    if item.get("future_value") is not None:
        return template_compound_response(item)
    return None


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
        compound_lines = [_compound_line(item) for item in tool_results if isinstance(item, dict)]
        compound_lines = [line for line in compound_lines if line]
        if compound_lines and len(compound_lines) == len(
            [i for i in tool_results if isinstance(i, dict) and i.get("future_value") is not None]
        ):
            body = compound_lines[0] if len(compound_lines) == 1 else "\n".join(compound_lines)
            return prefix + body
        body = template_multi_fx_response(tool_results)
        if body:
            return prefix + body

    if tool_result and tool_result.get("future_value") is not None:
        body = template_compound_response(tool_result)
        if body:
            return prefix + body

    if tool_result and tool_result.get("rate") is not None:
        body = template_fx_response(tool_result)
        if body:
            return prefix + body

    return None
