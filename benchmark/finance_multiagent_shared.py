"""Shared helpers for finance multi-agent containers E and F."""

from __future__ import annotations

import operator
import re
import time
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from benchmark.multiagent_measure import HopMetric
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from benchmark.workload import WorkloadTask
from chorusgraph.examples.finance_agent.nodes import _needs_fx_tool, _parse_fx_pair, _rate_in_text
from chorusgraph.transforms.intent import needs_compound_tool, parse_compound_params


class FinanceMultiAgentState(TypedDict, total=False):
    task: WorkloadTask
    message: str
    conversation_history: List[Dict[str, str]]
    context: str
    research_plan: str
    tool_plan: List[Dict[str, Any]]
    needs_tool: bool
    tool_result: Optional[Dict[str, Any]]
    tool_results: List[Any]
    tool_calls: List[Dict[str, Any]]
    draft_response: str
    response: str
    validation: Dict[str, Any]
    hop_metrics: Annotated[List[HopMetric], operator.add]
    cache_hit: bool
    cache_seed_phrases: List[str]
    latest_envelope_id: Optional[str]
    error: Optional[str]


def record_hop(
    state: FinanceMultiAgentState,
    name: str,
    started: float,
    gemini: InstrumentedGeminiClient,
    *,
    tools: int = 0,
) -> Dict[str, Any]:
    return {
        "hop_metrics": [
            HopMetric(
                hop=name,
                latency_ms=int((time.perf_counter() - started) * 1000),
                llm_calls=gemini.usage.llm_calls,
                tokens_in=gemini.usage.tokens_in,
                tokens_out=gemini.usage.tokens_out,
                tool_calls=tools,
            )
        ],
    }


def heuristic_tool_plan(message: str) -> tuple[List[Dict[str, Any]], str]:
    """Deterministic tool plan — same routing logic as finance researcher node."""
    compound_args = parse_compound_params(message)
    if compound_args:
        return (
            [{"tool": "compound_interest", "args": compound_args}],
            "Compute FV via compound_interest tool.",
        )

    if needs_compound_tool(message):
        return ([], "Compound query — no deterministic parse.")

    upper = message.upper()
    if "COMPARE" in upper or ("USD/EUR" in upper and "GBP" in upper):
        return (
            [
                {"tool": "fetch_exchange_rate", "args": {"from_currency": "USD", "to_currency": "EUR"}},
                {"tool": "fetch_exchange_rate", "args": {"from_currency": "USD", "to_currency": "GBP"}},
            ],
            "Fetch USD/EUR and USD/GBP for comparison.",
        )

    pair = _parse_fx_pair(message)
    if _needs_fx_tool(message) and pair:
        from_c, to_c = pair
        return (
            [{"tool": "fetch_exchange_rate", "args": {"from_currency": from_c, "to_currency": to_c}}],
            f"Fetch live {from_c}/{to_c}.",
        )

    return ([], "No live tool required.")


def validate_draft(
    draft: str,
    tool_result: Optional[Dict[str, Any]],
    gemini: InstrumentedGeminiClient,
) -> tuple[str, Dict[str, Any]]:
    """Rate/FV check + optional rewrite — shared by E and F."""
    from benchmark.shared.prompts import VALIDATOR_SYSTEM

    approved = True
    notes: List[str] = []
    out = draft

    if tool_result and "rate" in tool_result:
        rate = float(tool_result["rate"])
        if not _rate_in_text(rate, out):
            notes.append(f"Draft missing explicit rate {rate}")
            approved = False

    if tool_result and "future_value" in tool_result:
        fv = float(tool_result["future_value"])
        nums = re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.\d+", out)
        if not any(abs(float(n.replace(",", "")) - fv) <= 1.0 for n in nums):
            notes.append(f"Draft missing FV ~{fv}")
            approved = False

    if not approved and tool_result:
        user = (
            f"Draft:\n{out}\n\nTool data:\n{tool_result}\n\n"
            "Rewrite to include exact tool numbers. One short paragraph."
        )
        out = gemini.generate(VALIDATOR_SYSTEM, user)
        if tool_result.get("rate") and _rate_in_text(float(tool_result["rate"]), out):
            approved = True
            notes.append("validator=rewrite_ok")

    return out, {"approved": approved, "notes": notes}
