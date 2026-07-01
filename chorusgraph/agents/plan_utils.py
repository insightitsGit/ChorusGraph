"""Plan-Solve shared types and planner helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from chorusgraph.nodes.tool import ToolRegistry


PLANNER_SYSTEM = """You are a finance task planner. Given a user question, emit a STATIC JSON plan.

Available tools:
{tool_catalog}

Respond with JSON ONLY:
{{
  "steps": [
    {{"id": 1, "description": "...", "tool": "<tool_name>", "args": {{...}}}},
    ...
  ]
}}

Rules:
- Emit ALL steps upfront — no re-planning during execution.
- Use fetch_exchange_rate for FX pairs; compound_interest for deterministic calcs.
- For cross-rates, fetch both legs against a common base (e.g. USD) — do NOT invent a cross-rate tool.
- Keep steps minimal and ordered.
"""


@dataclass
class PlanStep:
    id: int
    description: str
    tool: str
    args: Dict[str, Any]


def _parse_plan_json(raw: str) -> List[PlanStep]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    steps = []
    for item in data.get("steps") or []:
        steps.append(
            PlanStep(
                id=int(item.get("id") or len(steps) + 1),
                description=str(item.get("description") or ""),
                tool=str(item.get("tool") or ""),
                args=dict(item.get("args") or {}),
            )
        )
    return steps


def _try_compute_cross(description: str, observations: List[Any]) -> Optional[Dict[str, Any]]:
    lower = description.lower()
    if "cross" not in lower and "compute" not in lower:
        return None
    usd_legs = []
    for obs in observations:
        data = obs.get("data") if isinstance(obs, dict) else obs
        if not isinstance(data, dict) or "rate" not in data:
            continue
        base = data.get("from_currency")
        quote = data.get("to_currency")
        if base == "USD":
            usd_legs.append((quote, float(data["rate"])))
    by_quote = {q: r for q, r in usd_legs}
    if "EUR" in by_quote and "GBP" in by_quote and by_quote["GBP"]:
        cross = by_quote["EUR"] / by_quote["GBP"]
        return {
            "from_currency": "EUR",
            "to_currency": "GBP",
            "rate": round(cross, 6),
            "source": "computed from USD legs",
        }
    return None


def plan_tasks(
    *,
    question: str,
    registry: ToolRegistry,
    llm_json: Callable[[str, str], str],
) -> List[PlanStep]:
    catalog = "\n".join(
        json.dumps({"name": n, "description": registry.get(n).description, "parameters": registry.get(n).parameters})
        for n in registry.names()
    )
    system = PLANNER_SYSTEM.format(tool_catalog=catalog)
    raw = llm_json(system, f"Question: {question}")
    return _parse_plan_json(raw)
