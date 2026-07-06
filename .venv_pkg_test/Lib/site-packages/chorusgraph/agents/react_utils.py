"""ReAct JSON parsing helpers."""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from chorusgraph.nodes.tool import ToolRegistry


def tool_catalog(registry: ToolRegistry) -> str:
    lines = []
    for name in registry.names():
        spec = registry.get(name)
        lines.append(json.dumps({"name": name, "description": spec.description, "parameters": spec.parameters}))
    return "\n".join(lines)


def parse_react_json(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise
